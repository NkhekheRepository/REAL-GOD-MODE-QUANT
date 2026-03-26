"""
Telegram Bot Handler for God Mode Quant Trading Orchestrator
Handles incoming commands, callbacks, and message processing
"""
import os
import logging
import json
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from flask import Flask, request, jsonify
import requests

logger = logging.getLogger(__name__)

# Try to import the dashboard
try:
    from telegram_dashboard import (
        TelegramDashboard,
        get_telegram_dashboard,
        init_telegram_dashboard
    )
except ImportError:
    TelegramDashboard = None
    get_telegram_dashboard = None
    init_telegram_dashboard = None


class BotState(Enum):
    """Bot interaction states"""
    IDLE = "idle"
    AWAITING_INPUT = "awaiting_input"
    CONFIRMING = "confirming"


@dataclass
class UserSession:
    """User session data for bot interactions"""
    user_id: int
    chat_id: int
    state: BotState = BotState.IDLE
    last_command: str = ""
    last_message_id: int = 0
    preferences: Dict[str, Any] = field(default_factory=dict)
    alert_enabled: bool = True


class TelegramBotHandler:
    """Telegram bot command handler with state management"""
    
    def __init__(self, bot_token: str, dashboard: TelegramDashboard = None):
        self.bot_token = bot_token
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.dashboard = dashboard
        
        # User sessions
        self._sessions: Dict[int, UserSession] = {}
        self._lock = threading.RLock()
        
        # Command handlers
        self._command_handlers: Dict[str, Callable] = {}
        self._callback_handlers: Dict[str, Callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
        
        # Flask app for webhook
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _register_default_handlers(self):
        """Register default command and callback handlers"""
        # These are handled by the dashboard
        self._callback_handlers = {
            "cmd_status": lambda cb, cid: self.dashboard._get_status_command([]) if self.dashboard else "Status unavailable",
            "cmd_positions": lambda cb, cid: self.dashboard._get_positions_command([]) if self.dashboard else "Positions unavailable",
            "cmd_risk": lambda cb, cid: self.dashboard._get_risk_command([]) if self.dashboard else "Risk report unavailable",
            "cmd_trust": lambda cb, cid: self.dashboard._get_trust_command([]) if self.dashboard else "Trust score unavailable",
            "cmd_pnl": lambda cb, cid: self.dashboard._get_pnl_command([]) if self.dashboard else "P&L unavailable",
            "cmd_summary": lambda cb, cid: self.dashboard._get_summary_command([]) if self.dashboard else "Summary unavailable",
            "cmd_engine": lambda cb, cid: self.dashboard._get_engine_command([]) if self.dashboard else "Engine unavailable",
            "cmd_leverage": lambda cb, cid: self.dashboard._get_leverage_command([]) if self.dashboard else "Leverage unavailable",
            "cmd_kelly": lambda cb, cid: self.dashboard._get_kelly_command([]) if self.dashboard else "Kelly unavailable",
            "cmd_strategies": lambda cb, cid: self.dashboard._get_strategies_command([]) if self.dashboard else "Strategies unavailable",
            "cmd_signal": lambda cb, cid: self.dashboard._get_signal_command([]) if self.dashboard else "Signal unavailable",
            "cmd_orders": lambda cb, cid: self.dashboard._get_orders_command([]) if self.dashboard else "Orders unavailable",
            "cmd_var": lambda cb, cid: self.dashboard._get_var_command([]) if self.dashboard else "VaR unavailable",
            "alerts_on": self._handle_alerts_on,
            "alerts_off": self._handle_alerts_off
        }
    
    def _handle_alerts_on(self, callback_data: str, chat_id: int) -> str:
        """Handle alerts on callback"""
        session = self._get_session(chat_id)
        if session:
            session.preferences['alerts_enabled'] = True
            session.alert_enabled = True
            return "\U0001F4E2 <b>Alerts Enabled</b>\n\nRisk and trade alerts are now active."
        return "\U0001F4E2 Alerts enabled"
    
    def _handle_alerts_off(self, callback_data: str, chat_id: int) -> str:
        """Handle alerts off callback"""
        session = self._get_session(chat_id)
        if session:
            session.preferences['alerts_enabled'] = False
            session.alert_enabled = False
            return "\U0001F6AB <b>Alerts Disabled</b>\n\nRisk and trade alerts are now muted."
        return "\U0001F6AB Alerts disabled"
    
    def _setup_routes(self):
        """Setup Flask routes for webhook"""
        self.app.add_url_rule('/webhook', 'webhook', self.handle_webhook, methods=['POST'])
        self.app.add_url_rule('/health', 'health', self._health_check)
    
    def _health_check(self):
        """Health check endpoint"""
        return jsonify({"status": "healthy", "service": "telegram-bot-handler"})
    
    def _get_session(self, user_id: int) -> Optional[UserSession]:
        """Get user session"""
        with self._lock:
            return self._sessions.get(user_id)
    
    def _create_session(self, user_id: int, chat_id: int) -> UserSession:
        """Create new user session"""
        with self._lock:
            session = UserSession(user_id=user_id, chat_id=chat_id)
            self._sessions[user_id] = session
            return session
    
    def _get_or_create_session(self, user_id: int, chat_id: int) -> UserSession:
        """Get or create user session"""
        session = self._get_session(user_id)
        if not session:
            session = self._create_session(user_id, chat_id)
        return session
    
    def handle_webhook(self):
        """Handle incoming Telegram webhook"""
        try:
            update = request.get_json()
            
            if not update:
                return jsonify({"ok": True})
            
            # Handle callback query (inline button press)
            if 'callback_query' in update:
                return self._handle_callback(update['callback_query'])
            
            # Handle message
            if 'message' in update:
                return self._handle_message(update['message'])
            
            return jsonify({"ok": True})
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
    
    def _handle_callback(self, callback_query: Dict) -> jsonify:
        """Handle inline keyboard button presses"""
        try:
            callback_data = callback_query.get('data', '')
            message = callback_query.get('message', {})
            chat = message.get('chat', {})
            
            chat_id = chat.get('id')
            message_id = message.get('message_id')
            
            if not chat_id:
                return jsonify({"ok": True})
            
            # Acknowledge the callback
            self._answer_callback(callback_query.get('id'))
            
            # Get handler
            handler = self._callback_handlers.get(callback_data)
            
            if handler:
                response = handler(callback_data, chat_id)
            else:
                response = f"Unknown action: {callback_data}"
            
            # Edit message with response
            self._edit_message(chat_id, message_id, response)
            
            return jsonify({"ok": True})
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
    
    def _handle_message_simple(self, message: Dict) -> bool:
        """Handle incoming messages (simplified for polling, no Flask response)"""
        try:
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            user = message.get('from', {})
            user_id = user.get('id')
            text = message.get('text', '')
            message_id = message.get('message_id')
            
            if not chat_id or not text:
                return True
            
            session = self._get_or_create_session(user_id, chat_id)
            session.last_message_id = message_id
            
            if text.startswith('/'):
                return self._handle_command_simple(text, chat_id, user_id, session)
            
            if session.state == BotState.AWAITING_INPUT:
                session.state = BotState.IDLE
            
            if self.dashboard:
                response = self.dashboard._get_help_command([])
            else:
                response = "Bot is running. Use /help for commands."
            
            self._send_message(chat_id, response)
            return True
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return False
    
    def _handle_callback_simple(self, callback_query: Dict) -> bool:
        """Handle inline keyboard button presses (simplified for polling)"""
        try:
            callback_data = callback_query.get('data', '')
            message = callback_query.get('message', {})
            chat = message.get('chat', {})
            
            chat_id = chat.get('id')
            message_id = message.get('message_id')
            
            if not chat_id:
                return True
            
            self._answer_callback(callback_query.get('id'))
            
            handler = self._callback_handlers.get(callback_data)
            
            if handler:
                response = handler(callback_data, chat_id)
            else:
                response = f"Unknown action: {callback_data}"
            
            self._edit_message(chat_id, message_id, response)
            return True
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            return False
    
    def _handle_command_simple(self, text: str, chat_id: int, user_id: int, session: UserSession) -> bool:
        """Handle bot commands (simplified for polling)"""
        command_parts = text[1:].split()
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        session.last_command = command
        
        logger.info(f"Handling command: /{command} for chat {chat_id}")
        
        if self.dashboard:
            response = self.dashboard.handle_command(command, args)
            logger.info(f"Dashboard response type: {type(response)}, value: {response[:100] if response else 'None'}...")
        else:
            response = f"Command /{command} received"
        
        # Send response
        sent = self._send_message(chat_id, response)
        logger.info(f"Message sent: {sent}")
        
        return True
    
    def _handle_message(self, message: Dict) -> jsonify:
        """Handle incoming messages"""
        try:
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            user = message.get('from', {})
            user_id = user.get('id')
            text = message.get('text', '')
            message_id = message.get('message_id')
            
            if not chat_id or not text:
                return jsonify({"ok": True})
            
            # Create or get session
            session = self._get_or_create_session(user_id, chat_id)
            session.last_message_id = message_id
            
            # Check if it's a command
            if text.startswith('/'):
                return self._handle_command(text, chat_id, user_id, session)
            
            # Handle stateful input (if awaiting input)
            if session.state == BotState.AWAITING_INPUT:
                return self._handle_input(text, chat_id, session)
            
            # Default: show help
            if self.dashboard:
                response = self.dashboard._get_help_command([])
            else:
                response = "Bot is running. Use /help for commands."
            
            self._send_message(chat_id, response)
            return jsonify({"ok": True})
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
    
    def _handle_command(self, text: str, chat_id: int, user_id: int, session: UserSession) -> jsonify:
        """Handle bot commands"""
        command_parts = text[1:].split()
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        session.last_command = command
        
        # Get response from dashboard
        if self.dashboard:
            response = self.dashboard.handle_command(command, args)
        else:
            response = f"Command /{command} received"
        
        # Send response
        self._send_message(chat_id, response)
        
        return jsonify({"ok": True})
    
    def _handle_input(self, text: str, chat_id: int, session: UserSession) -> jsonify:
        """Handle user input in specific states"""
        # For future stateful interactions
        session.state = BotState.IDLE
        return jsonify({"ok": True})
    
    def _send_message(self, chat_id: int, text: str, 
                     reply_markup: Optional[Dict] = None) -> bool:
        """Send message to Telegram"""
        url = f"{self.api_base}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def _edit_message(self, chat_id: int, message_id: int, text: str) -> bool:
        """Edit existing message"""
        url = f"{self.api_base}/editMessageText"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return False
    
    def _answer_callback(self, callback_query_id: str) -> bool:
        """Answer callback query (acknowledge button press)"""
        url = f"{self.api_base}/answerCallbackQuery"
        payload = {
            'callback_query_id': callback_query_id
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to answer callback: {e}")
            return False
    
    def set_webhook(self, webhook_url: str) -> bool:
        """Set Telegram webhook URL"""
        url = f"{self.api_base}/setWebhook"
        payload = {
            'url': webhook_url
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Webhook set to {webhook_url}")
                return True
            else:
                logger.error(f"Failed to set webhook: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False
    
    def delete_webhook(self) -> bool:
        """Delete Telegram webhook"""
        url = f"{self.api_base}/deleteWebhook"
        
        try:
            response = requests.post(url, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False
    
    def get_me(self) -> Optional[Dict]:
        """Get bot information"""
        url = f"{self.api_base}/getMe"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get('result')
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return None
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """Run the Flask server for webhook handling"""
        logger.info(f"Starting Telegram bot handler on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)
    
    def start_polling(self, timeout: int = 10):
        """Start polling for updates (alternative to webhooks)"""
        offset = None  # Start with None to get latest updates
        logger.info("Starting polling loop")
        
        while True:
            try:
                url = f"{self.api_base}/getUpdates"
                params = {'timeout': timeout}
                if offset is not None:
                    params['offset'] = offset
                
                logger.info(f"Polling with offset: {offset}")
                response = requests.get(url, params=params, timeout=timeout + 10)
                response.raise_for_status()
                result = response.json()
                
                if not result.get('ok'):
                    logger.error(f"Polling API error: {result}")
                    continue
                
                if result.get('ok'):
                    updates = result.get('result', [])
                    logger.info(f"Polling: got {len(updates)} updates")
                    
                    if updates:
                        logger.info(f"Processing {len(updates)} updates")
                        for update in updates:
                            offset = update.get('update_id', 0) + 1
                            logger.info(f"Processing update {offset}")
                            
                            try:
                                if 'message' in update:
                                    msg = update['message']
                                    logger.info(f"Got message: {msg.get('text', '')[:50]}")
                                    self._handle_message_simple(msg)
                                elif 'callback_query' in update:
                                    self._handle_callback_simple(update['callback_query'])
                            except Exception as e:
                                logger.error(f"Error processing update: {e}")
                                
            except requests.exceptions.ReadTimeout:
                continue
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)


# Global bot handler instance
_bot_handler: Optional[TelegramBotHandler] = None


def init_telegram_bot(bot_token: str = None, webhook_url: str = None, dashboard: Any = None) -> TelegramBotHandler:
    """Initialize Telegram bot handler"""
    global _bot_handler
    
    if bot_token is None:
        from security.secrets_manager import get_telegram_bot_token
        bot_token = get_telegram_bot_token() or os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        raise ValueError("Telegram bot token is required")
    
    # Use provided dashboard or try to get it
    if dashboard is None:
        try:
            from telegram_dashboard import get_telegram_dashboard
            dashboard = get_telegram_dashboard()
        except Exception as e:
            logger.warning(f"Could not get dashboard: {e}")
    
    logger.info(f"Initializing bot handler with dashboard: {dashboard is not None}")
    
    _bot_handler = TelegramBotHandler(bot_token, dashboard)
    
    # Set webhook if provided
    if webhook_url:
        _bot_handler.set_webhook(webhook_url)
    else:
        # Use polling as fallback
        logger.info("No webhook URL provided, using polling")
    
    logger.info("Telegram bot handler initialized")
    
    return _bot_handler


def get_telegram_bot() -> Optional[TelegramBotHandler]:
    """Get the global bot handler instance"""
    return _bot_handler


# Flask app for the bot handler
def create_bot_app(bot_token: str = None, webhook_url: str = None) -> Flask:
    """Create Flask app for bot handler"""
    global _bot_handler
    
    if bot_token is None:
        from security.secrets_manager import get_telegram_bot_token
        bot_token = get_telegram_bot_token() or os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Initialize bot handler
    _bot_handler = init_telegram_bot(bot_token, webhook_url)
    
    return _bot_handler.app
