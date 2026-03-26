"""
Telegram Dashboard for God Mode Quant Trading Orchestrator
Provides comprehensive real-time monitoring, command handlers, and inline keyboards
"""
import os
import logging
import time
import json
import threading
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class TelegramMessageType(Enum):
    """Types of Telegram messages"""
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    RISK_ALERT = "risk_alert"
    TRUST_CHANGE = "trust_change"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    SYSTEM = "system"


class TelegramEmoji(Enum):
    """Emojis for different message types"""
    # Trading
    LONG = "\U0001F4C8"   # Chart upward
    SHORT = "\U0001F4C9"  # Chart downward
    ENTRY = "\U00002705"  # Check mark
    EXIT = "\U0000274C"   # Cross mark
    PROFIT = "\U0001F4B0" # Money bag
    LOSS = "\U0001F4B3"   # Money with wings
    
    # Risk
    WARNING = "\U000026A0"  # Warning
    DANGER = "\U0001F6AB"   # Prohibited
    SHIELD = "\U0001F6E1"  # Shield
    
    # Trust
    TRUST_HIGH = "\U0001F3AF"  # Target
    TRUST_MED = "\U0001F50D"   # Magnifying glass
    TRUST_LOW = "\U0001F6D1"   # Stop sign
    
    # System
    ROBOT = "\U0001F916"   # Robot
    HEART = "\U00002764"    # Heart
    GEAR = "\U00002699"     # Gear
    CLOCK = "\U000023F0"   # Alarm clock
    STATS = "\U0001F4CA"    # Bar chart
    FIRE = "\U0001F525"     # Fire
    ICE = "\U0001F9CA"      # Ice


@dataclass
class TradeNotification:
    """Trade execution notification data"""
    symbol: str
    side: str  # LONG or SHORT
    quantity: float
    entry_price: float
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    strategy: str = "unknown"


@dataclass
class RiskAlertNotification:
    """Risk alert notification data"""
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class TrustChangeNotification:
    """Trust score change notification"""
    service_or_user: str
    old_score: float
    new_score: float
    change_reason: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class DailySummary:
    """Daily summary data"""
    date: str
    total_trades: int
    profitable_trades: int
    losing_trades: int
    total_pnl: float
    win_rate: float
    max_drawdown: float
    portfolio_value: float
    open_positions: int
    trust_score: float


class TelegramDashboard:
    """Comprehensive Telegram dashboard for trading orchestrator"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        
        # State for tracking
        self._lock = threading.RLock()
        self.trade_history: List[TradeNotification] = []
        self.last_trust_score: Dict[str, float] = {}
        self.daily_stats: Dict[str, Any] = {
            "trades": 0,
            "profitable": 0,
            "losing": 0,
            "pnl": 0.0,
            "start_value": 0.0,
            "start_time": time.time()
        }
        
        # Configuration
        self.alert_thresholds = {
            "max_drawdown": 10.0,        # 10% max drawdown
            "max_position_risk": 2.0,    # 2% per position
            "max_portfolio_risk": 5.0,   # 5% total portfolio
            "trust_score_low": 50.0,      # Alert if below 50
            "trust_score_critical": 30.0 # Critical if below 30
        }
        
        # Rate limiting
        self.last_alert_time: Dict[str, float] = {}
        self.alert_cooldown = 300  # 5 minutes between alerts of same type
        
        # Prometheus metrics integration
        self._setup_prometheus_exporters()
    
    def _setup_prometheus_exporters(self):
        """Setup Prometheus metrics for Telegram dashboard"""
        try:
            from prometheus_client import Counter, Gauge, Histogram, Info
            from prometheus_client import start_http_server
            from prometheus_client import REGISTRY
            
            # Telegram metrics
            self.telegram_messages_sent = Counter(
                'telegram_messages_sent_total',
                'Total Telegram messages sent',
                ['message_type', 'status']
            )
            
            self.telegram_last_message_time = Gauge(
                'telegram_last_message_timestamp',
                'Timestamp of last Telegram message',
                ['message_type']
            )
            
            self.telegram_command_count = Counter(
                'telegram_commands_received_total',
                'Total Telegram commands received',
                ['command']
            )
            
            self.active_positions_gauge = Gauge(
                'trading_active_positions',
                'Current number of active positions'
            )
            
            self.pnl_gauge = Gauge(
                'trading_unrealized_pnl_dollars',
                'Unrealized P&L in dollars'
            )
            
            self.trust_score_gauge = Gauge(
                'security_trust_score',
                'Current trust score'
            )
            
            self.risk_alert_count = Counter(
                'risk_alerts_triggered_total',
                'Total risk alerts triggered',
                ['alert_type', 'severity']
            )
            
            logger.info("Prometheus metrics initialized for Telegram dashboard")
            
        except ImportError:
            logger.warning("prometheus_client not available, skipping metrics setup")
            self.telegram_messages_sent = None
            self.telegram_last_message_time = None
            self.telegram_command_count = None
            self.active_positions_gauge = None
            self.pnl_gauge = None
            self.trust_score_gauge = None
            self.risk_alert_count = None
    
    def _increment_metric(self, metric, labels=None, value=1):
        """Safely increment a Prometheus metric"""
        if metric is not None:
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
    
    def _set_metric(self, metric, labels=None, value=0):
        """Safely set a Prometheus gauge metric"""
        if metric is not None:
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
    
    def _should_send_alert(self, alert_type: str) -> bool:
        """Check if enough time has passed since last alert of this type"""
        current_time = time.time()
        last_time = self.last_alert_time.get(alert_type, 0)
        
        if current_time - last_time >= self.alert_cooldown:
            self.last_alert_time[alert_type] = current_time
            return True
        return False
    
    def _format_price(self, price: float) -> str:
        """Format price with appropriate decimal places"""
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:,.4f}"
        else:
            return f"{price:,.8f}"
    
    def _format_pnl(self, pnl: float) -> Tuple[str, str]:
        """Format P&L with emoji and color"""
        if pnl > 0:
            return f"+{self._format_price(pnl)}", TelegramEmoji.PROFIT.value
        elif pnl < 0:
            return f"-{self._format_price(abs(pnl))}", TelegramEmoji.LOSS.value
        else:
            return "0.00", TelegramEmoji.ENTRY.value
    
    def _send_message(self, text: str, parse_mode: str = 'HTML',
                     reply_markup: Optional[Dict] = None) -> bool:
        """Send message to Telegram"""
        url = f"{self.api_base}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Telegram message sent successfully: {text[:50]}...")
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def _get_inline_keyboard(self) -> Dict:
        """Get standard inline keyboard with quick actions"""
        return {
            "inline_keyboard": [
                [
                    {"text": "\U0001F4C8 Status", "callback_data": "cmd_status"},
                    {"text": "\U0001F4CA Positions", "callback_data": "cmd_positions"},
                    {"text": "\U0001F3AF Signal", "callback_data": "cmd_signal"}
                ],
                [
                    {"text": "\U0001F6E1 Risk", "callback_data": "cmd_risk"},
                    {"text": "\U0001F4C8 VaR", "callback_data": "cmd_var"},
                    {"text": "\U0001F3AF Kelly", "callback_data": "cmd_kelly"}
                ],
                [
                    {"text": "\U0001F916 Engine", "callback_data": "cmd_engine"},
                    {"text": "\u26A1 Leverage", "callback_data": "cmd_leverage"},
                    {"text": "\U0001F4CA Strategies", "callback_data": "cmd_strategies"}
                ],
                [
                    {"text": "\U0001F4B0 P&L", "callback_data": "cmd_pnl"},
                    {"text": "\U0001F4CB Orders", "callback_data": "cmd_orders"},
                    {"text": "\U0001F4CB Summary", "callback_data": "cmd_summary"}
                ],
                [
                    {"text": "\U0001F4E2 Alerts On", "callback_data": "alerts_on"},
                    {"text": "\U0001F6AB Alerts Off", "callback_data": "alerts_off"}
                ]
            ]
        }
    
    # ==================== TRADE NOTIFICATIONS ====================
    
    def send_trade_entry(self, trade: TradeNotification) -> bool:
        """Send trade entry notification with detailed info"""
        emoji = TelegramEmoji.LONG.value if trade.side.upper() == "LONG" else TelegramEmoji.SHORT.value
        
        message = (
            f"{emoji} <b>TRADE ENTRY</b>\n\n"
            f"<b>Symbol:</b> {trade.symbol}\n"
            f"<b>Side:</b> {trade.side.upper()}\n"
            f"<b>Quantity:</b> {trade.quantity:.6f}\n"
            f"<b>Entry Price:</b> {self._format_price(trade.entry_price)}\n"
            f"<b>Strategy:</b> {trade.strategy}\n"
        )
        
        if trade.stop_loss:
            message += f"<b>Stop Loss:</b> {self._format_price(trade.stop_loss)}\n"
        if trade.take_profit:
            message += f"<b>Take Profit:</b> {self._format_price(trade.take_profit)}\n"
        
        message += f"\n\U000023F0 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Store in history
        with self._lock:
            self.trade_history.append(trade)
            self.daily_stats["trades"] += 1
        
        # Update metrics
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "trade_entry", "status": "sent"}
        )
        self._set_metric(
            self.telegram_last_message_time,
            {"message_type": "trade_entry"},
            time.time()
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    def send_trade_exit(self, trade: TradeNotification) -> bool:
        """Send trade exit notification with P&L"""
        pnl_str, pnl_emoji = self._format_pnl(trade.pnl or 0)
        
        message = (
            f"{pnl_emoji} <b>TRADE EXIT</b>\n\n"
            f"<b>Symbol:</b> {trade.symbol}\n"
            f"<b>Side:</b> {trade.side.upper()}\n"
            f"<b>Quantity:</b> {trade.quantity:.6f}\n"
            f"<b>Entry Price:</b> {self._format_price(trade.entry_price)}\n"
            f"<b>Exit Price:</b> {self._format_price(trade.current_price or trade.entry_price)}\n"
            f"<b>P&L:</b> {pnl_str}"
        )
        
        if trade.pnl_percent is not None:
            pct_str = f"+{trade.pnl_percent:.2f}%" if trade.pnl_percent > 0 else f"{trade.pnl_percent:.2f}%"
            message += f" ({pct_str})"
        
        message += f"\n\n\U000023F0 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Update daily stats
        with self._lock:
            if trade.pnl and trade.pnl > 0:
                self.daily_stats["profitable"] += 1
            else:
                self.daily_stats["losing"] += 1
            if trade.pnl:
                self.daily_stats["pnl"] += trade.pnl
        
        # Update metrics
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "trade_exit", "status": "sent"}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    # ==================== RISK ALERTS ====================
    
    def send_risk_alert(self, alert: RiskAlertNotification) -> bool:
        """Send risk alert notification"""
        severity_emoji = {
            "LOW": TelegramEmoji.WARNING.value,
            "MEDIUM": TelegramEmoji.WARNING.value,
            "HIGH": TelegramEmoji.DANGER.value,
            "CRITICAL": "\U0001F6A8"
        }.get(alert.severity.upper(), TelegramEmoji.WARNING.value)
        
        color = {
            "LOW": "#FFA500",
            "MEDIUM": "#FF8C00",
            "HIGH": "#FF4500",
            "CRITICAL": "#FF0000"
        }.get(alert.severity.upper(), "#FFA500")
        
        message = (
            f"{severity_emoji} <b>RISK ALERT</b>\n\n"
            f"<b>Type:</b> {alert.alert_type}\n"
            f"<b>Severity:</b> <code>{alert.severity.upper()}</code>\n\n"
            f"<b>Message:</b> {alert.message}\n"
        )
        
        if alert.details:
            message += "\n<b>Details:</b>\n"
            for key, value in alert.details.items():
                message += f"  \u2022 {key}: {value}\n"
        
        message += f"\n\U000023F0 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Check cooldown before sending
        alert_type_key = f"risk_{alert.alert_type}"
        if not self._should_send_alert(alert_type_key):
            logger.info(f"Risk alert rate limited: {alert.alert_type}")
            return False
        
        # Update metrics
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "risk_alert", "status": "sent"}
        )
        self._increment_metric(
            self.risk_alert_count,
            {"alert_type": alert.alert_type, "severity": alert.severity.lower()}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    def check_and_send_position_limit_alert(self, symbol: str, position_risk: float) -> bool:
        """Check position risk limit and send alert if exceeded"""
        if position_risk > self.alert_thresholds["max_position_risk"]:
            alert = RiskAlertNotification(
                alert_type="position_limit",
                severity="HIGH" if position_risk > self.alert_thresholds["max_position_risk"] * 2 else "MEDIUM",
                message=f"Position {symbol} risk exceeds limit",
                details={
                    "position_risk_percent": f"{position_risk:.2f}%",
                    "limit": f"{self.alert_thresholds['max_position_risk']:.2f}%"
                }
            )
            return self.send_risk_alert(alert)
        return False
    
    def check_and_send_drawdown_alert(self, current_drawdown: float, portfolio_value: float) -> bool:
        """Check drawdown and send alert if limit exceeded"""
        if current_drawdown > self.alert_thresholds["max_drawdown"]:
            severity = "CRITICAL" if current_drawdown > self.alert_thresholds["max_drawdown"] * 1.5 else "HIGH"
            alert = RiskAlertNotification(
                alert_type="drawdown",
                severity=severity,
                message=f"Portfolio drawdown exceeds limit",
                details={
                    "current_drawdown": f"{current_drawdown:.2f}%",
                    "limit": f"{self.alert_thresholds['max_drawdown']:.2f}%",
                    "portfolio_value": self._format_price(portfolio_value)
                }
            )
            return self.send_risk_alert(alert)
        return False
    
    def check_and_send_portfolio_risk_alert(self, portfolio_risk: float) -> bool:
        """Check portfolio risk and send alert if exceeded"""
        if portfolio_risk > self.alert_thresholds["max_portfolio_risk"]:
            alert = RiskAlertNotification(
                alert_type="portfolio_risk",
                severity="HIGH",
                message=f"Total portfolio risk exceeds limit",
                details={
                    "total_risk_percent": f"{portfolio_risk:.2f}%",
                    "limit": f"{self.alert_thresholds['max_portfolio_risk']:.2f}%"
                }
            )
            return self.send_risk_alert(alert)
        return False
    
    # ==================== TRUST SCORE NOTIFICATIONS ====================
    
    def send_trust_change_alert(self, change: TrustChangeNotification) -> bool:
        """Send trust score change notification"""
        if change.old_score == change.new_score:
            return False
        
        # Determine severity based on score level
        if change.new_score < self.alert_thresholds["trust_score_critical"]:
            severity_emoji = TelegramEmoji.DANGER.value
            severity = "CRITICAL"
        elif change.new_score < self.alert_thresholds["trust_score_low"]:
            severity_emoji = TelegramEmoji.WARNING.value
            severity = "HIGH"
        else:
            severity_emoji = TelegramEmoji.TRUST_MED.value
            severity = "LOW"
        
        diff = change.new_score - change.old_score
        diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"
        
        message = (
            f"{severity_emoji} <b>TRUST SCORE CHANGE</b>\n\n"
            f"<b>Service:</b> {change.service_or_user}\n"
            f"<b>Old Score:</b> {change.old_score:.1f}\n"
            f"<b>New Score:</b> <code>{change.new_score:.1f}</code>\n"
            f"<b>Change:</b> {diff_str}\n"
            f"<b>Reason:</b> {change.change_reason}\n"
        )
        
        if change.new_score < self.alert_thresholds["trust_score_low"]:
            message += f"\n\U000026A0 <b>Action Required:</b> Trust score below threshold!"
        
        message += f"\n\U000023F0 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Only send alert if significant change or below threshold
        if abs(diff) > 5 or change.new_score < self.alert_thresholds["trust_score_low"]:
            self._increment_metric(
                self.telegram_messages_sent,
                {"message_type": "trust_change", "status": "sent"}
            )
            return self._send_message(message, reply_markup=self._get_inline_keyboard())
        return False
    
    def check_trust_score_change(self, service_or_user: str, new_score: float):
        """Check if trust score changed significantly and send notification"""
        with self._lock:
            old_score = self.last_trust_score.get(service_or_user, new_score)
            
            if old_score != new_score:
                change = TrustChangeNotification(
                    service_or_user=service_or_user,
                    old_score=old_score,
                    new_score=new_score,
                    change_reason="Trust score updated"
                )
                self.last_trust_score[service_or_user] = new_score
                
                # Update metrics
                self._set_metric(
                    self.trust_score_gauge,
                    value=new_score
                )
                
                return self.send_trust_change_alert(change)
        return False
    
    # ==================== SUMMARY REPORTS ====================
    
    def send_daily_summary(self, risk_report: Optional[Dict] = None,
                          trust_score: Optional[float] = None) -> bool:
        """Send daily summary report"""
        with self._lock:
            stats = self.daily_stats.copy()
        
        # Calculate win rate
        total_trades = stats.get("trades", 0)
        win_rate = (stats.get("profitable", 0) / total_trades * 100) if total_trades > 0 else 0
        
        # Get P&L
        pnl = stats.get("pnl", 0)
        pnl_str, pnl_emoji = self._format_pnl(pnl)
        
        message = (
            f"\U0001F4CA <b>DAILY SUMMARY</b>\n\n"
            f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}\n"
            f"<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"<b>Trades:</b> {total_trades}\n"
            f"  \u2705 Profitable: {stats.get('profitable', 0)}\n"
            f"  \u274C Losing: {stats.get('losing', 0)}\n"
            f"  \U0001F3AF Win Rate: {win_rate:.1f}%\n\n"
            f"<b>P&L:</b> {pnl_emoji} {pnl_str}\n"
        )
        
        if risk_report:
            portfolio = risk_report.get("portfolio", {})
            message += (
                f"\n<b>Portfolio:</b>\n"
                f"  Value: {self._format_price(portfolio.get('total_value', 0))}\n"
                f"  Positions: {portfolio.get('position_count', 0)}\n"
                f"  Unrealized P&L: {self._format_price(portfolio.get('total_unrealized_pnl', 0))}\n"
                f"  Max Drawdown: {portfolio.get('max_drawdown', 0):.2f}%\n"
            )
        
        if trust_score is not None:
            trust_emoji = (
                TelegramEmoji.TRUST_HIGH.value if trust_score > 70
                else TelegramEmoji.TRUST_MED.value if trust_score > 40
                else TelegramEmoji.TRUST_LOW.value
            )
            message += f"\n{trust_emoji} <b>Trust Score:</b> {trust_score:.1f}"
        
        message += f"\n\n\U0001F4E2 Next update at midnight"
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "daily_summary", "status": "sent"}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    def send_weekly_summary(self, risk_report: Optional[Dict] = None) -> bool:
        """Send weekly summary report"""
        with self._lock:
            stats = self.daily_stats.copy()
        
        message = (
            f"\U0001F4CA <b>WEEKLY SUMMARY</b>\n\n"
            f"<b>Week:</b> {datetime.now().strftime('%Y-W%W')}\n"
            f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"<b>This Week's Stats:</b>\n"
            f"  Total Trades: {stats.get('trades', 0)}\n"
            f"  Profitable: {stats.get('profitable', 0)}\n"
            f"  Losing: {stats.get('losing', 0)}\n"
            f"  Total P&L: {self._format_price(stats.get('pnl', 0))}\n"
        )
        
        if risk_report:
            portfolio = risk_report.get("portfolio", {})
            message += (
                f"\n<b>Current Portfolio:</b>\n"
                f"  Value: {self._format_price(portfolio.get('total_value', 0))}\n"
                f"  Positions: {portfolio.get('position_count', 0)}\n"
                f"  Max Drawdown: {portfolio.get('max_drawdown', 0):.2f}%\n"
            )
        
        message += f"\n\U0001F4E2 Have a great week!"
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "weekly_summary", "status": "sent"}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    # ==================== COMMAND HANDLERS ====================
    
    def handle_command(self, command: str, args: List[str] = None) -> str:
        """Handle incoming Telegram commands"""
        command = command.lower().strip('/')
        
        # Update command metrics
        self._increment_metric(
            self.telegram_command_count,
            {"command": command}
        )
        
        handlers = {
            'status': self._get_status_command,
            'positions': self._get_positions_command,
            'risk': self._get_risk_command,
            'trust': self._get_trust_command,
            'help': self._get_help_command,
            'pnl': self._get_pnl_command,
            'summary': self._get_summary_command,
            'alerts': self._get_alerts_command,
            'leverage': self._get_leverage_command,
            'kelly': self._get_kelly_command,
            'strategies': self._get_strategies_command,
            'signal': self._get_signal_command,
            'orders': self._get_orders_command,
            'var': self._get_var_command,
            'engine': self._get_engine_command,
            'start': self._get_start_command,
            'stop': self._get_stop_command,
        }
        
        handler = handlers.get(command)
        if handler:
            return handler(args)
        else:
            return self._get_unknown_command(command)
    
    def _get_status_command(self, args: List[str]) -> str:
        """Get overall status"""
        from risk_management import risk_manager
        from security.trust_scorer import trust_scorer
        
        portfolio = risk_manager.portfolio
        trust_score = trust_scorer.get_trust_score("orchestrator:system")
        
        pnl = portfolio.total_unrealized_pnl
        pnl_str, pnl_emoji = self._format_pnl(pnl)
        
        should_stop, reasons = risk_manager.should_stop_trading()
        
        message = (
            f"\U0001F916 <b>SYSTEM STATUS</b>\n\n"
            f"<b>Portfolio Value:</b> {self._format_price(portfolio.total_value)}\n"
            f"<b>Unrealized P&L:</b> {pnl_emoji} {pnl_str}\n"
            f"<b>Positions:</b> {portfolio.position_count}\n"
            f"<b>Cash:</b> {self._format_price(portfolio.cash)}\n"
            f"<b>Max Drawdown:</b> {portfolio.max_drawdown:.2f}%\n\n"
            f"{TelegramEmoji.TRUST_HIGH.value if trust_score > 70 else TelegramEmoji.TRUST_MED.value if trust_score > 40 else TelegramEmoji.TRUST_LOW.value} "
            f"<b>Trust Score:</b> {trust_score:.1f}\n\n"
        )
        
        if should_stop:
            message += f"\U0001F6AB <b>TRADING PAUSED</b>\n"
            for reason in reasons:
                message += f"  \u2022 {reason}\n"
        else:
            message += f"\U0001F4B0 <b>Trading Active</b>"
        
        return message
    
    def _get_positions_command(self, args: List[str]) -> str:
        """Get open positions"""
        from risk_management import risk_manager
        
        positions = risk_manager.portfolio.positions
        
        if not positions:
            return f"\U0001F4CB <b>OPEN POSITIONS</b>\n\nNo open positions currently."
        
        message = f"\U0001F4CB <b>OPEN POSITIONS</b> ({len(positions)})\n\n"
        
        for symbol, pos in positions.items():
            side = "LONG" if pos.quantity > 0 else "SHORT"
            emoji = TelegramEmoji.LONG.value if pos.quantity > 0 else TelegramEmoji.SHORT.value
            
            pnl_str, pnl_emoji = self._format_pnl(pos.unrealized_pnl)
            pct = pos.unrealized_pnl_percent
            
            message += (
                f"{emoji} <b>{symbol}</b>\n"
                f"  Side: {side} | Qty: {abs(pos.quantity):.4f}\n"
                f"  Entry: {self._format_price(pos.entry_price)}\n"
                f"  Current: {self._format_price(pos.current_price)}\n"
                f"  P&L: {pnl_emoji} {pnl_str} ({pct:+.2f}%)\n"
            )
            
            if pos.stop_loss:
                message += f"  SL: {self._format_price(pos.stop_loss)} | "
            if pos.take_profit:
                message += f"TP: {self._format_price(pos.take_profit)}\n"
            
            message += "\n"
        
        return message
    
    def _get_risk_command(self, args: List[str]) -> str:
        """Get risk report"""
        from risk_management import risk_manager
        
        report = risk_manager.get_risk_report()
        
        portfolio = report["portfolio"]
        limits = report["risk_limits"]
        status = report["risk_status"]
        
        message = (
            f"\U0001F6E1 <b>RISK REPORT</b>\n\n"
            f"<b>Portfolio Risk:</b> {portfolio['total_risk_percent']:.2f}%\n"
            f"  Limit: {limits['max_portfolio_risk_percent']:.2f}%\n"
            f"  Utilization: {status.get('portfolio_risk_utilization', 0):.1f}%\n\n"
            f"<b>Max Drawdown:</b> {portfolio['max_drawdown']:.2f}%\n"
            f"  Limit: {limits['max_drawdown_percent']:.2f}%\n\n"
            f"<b>Position Limits:</b>\n"
            f"  Max per position: {limits['max_position_risk_percent']:.2f}%\n"
        )
        
        if portfolio.get('positions'):
            message += f"\n<b>Positions at Risk:</b>\n"
            for symbol, pos in portfolio['positions'].items():
                if pos['risk_percent'] > 0:
                    message += f"  \u2022 {symbol}: {pos['risk_percent']:.2f}%\n"
        
        if status['should_stop_trading']:
            message += f"\n\U0001F6AB <b>TRADING STOPPED</b>\n"
            for reason in status['stop_reasons']:
                message += f"  \u2022 {reason}\n"
        else:
            message += f"\n\U0001F4B0 <b>Risk OK</b>"
        
        return message
    
    def _get_trust_command(self, args: List[str]) -> str:
        """Get trust score"""
        from security.trust_scorer import trust_scorer
        
        service_or_user = args[0] if args else "orchestrator:system"
        
        report = trust_scorer.get_trust_report(service_or_user)
        
        if "error" in report:
            return f"\U0001F6AB <b>ERROR</b>\n\n{report['error']}"
        
        score = report['current_score']
        is_trustworthy = report.get('is_trustworthy', False)
        needs_attention = report.get('needs_attention', False)
        
        emoji = (
            TelegramEmoji.TRUST_HIGH.value if score > 70
            else TelegramEmoji.TRUST_MED.value if score > 40
            else TelegramEmoji.TRUST_LOW.value
        )
        
        status = "OK" if is_trustworthy else "NEEDS ATTENTION" if needs_attention else "WARNING"
        
        message = (
            f"{emoji} <b>TRUST SCORE</b>\n\n"
            f"<b>Service:</b> {report['service_or_user']}\n"
            f"<b>Current Score:</b> <code>{score:.1f}</code> / 100\n"
            f"<b>Status:</b> {status}\n\n"
            f"<b>Last Updated:</b> {datetime.fromtimestamp(report['last_updated']).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"<b>Recent Events (24h):</b> {report.get('recent_events_count', 0)}\n"
            f"<b>24h Weight Change:</b> {report.get('recent_24h_weight', 0):+.1f}\n"
        )
        
        return message
    
    def _get_help_command(self, args: List[str]) -> str:
        """Get help message with all commands"""
        return (
            f"\U0001F916 <b>GOD MODE QUANT BOT</b>\n\n"
            f"<b>Trading Commands:</b>\n"
            f"\U0001F4C8 <b>/status</b> - Portfolio and system status\n"
            f"\U0001F4CA <b>/positions</b> - Open positions\n"
            f"\U0001F4B0 <b>/pnl</b> - P&L summary\n"
            f"\U0001F4CB <b>/orders</b> - Open orders & positions\n"
            f"\U0001F3AF <b>/signal</b> - Current trading signal\n\n"
            f"<b>Engine Commands:</b>\n"
            f"\U0001F916 <b>/engine</b> - Engine status\n"
            f"\U0001F7E2 <b>/start</b> - Start trading engine\n"
            f"\U0001F534 <b>/stop</b> - Stop trading engine\n"
            f"\u26A1 <b>/leverage</b> - Get/set leverage\n\n"
            f"<b>Risk Commands:</b>\n"
            f"\U0001F6E1 <b>/risk</b> - Risk report\n"
            f"\U0001F4C8 <b>/var</b> - Value at Risk\n"
            f"\U0001F3AF <b>/kelly</b> - Kelly Criterion stats\n\n"
            f"<b>Strategy Commands:</b>\n"
            f"\U0001F4CA <b>/strategies</b> - Strategy router status\n\n"
            f"<b>System Commands:</b>\n"
            f"\U0001F3AF <b>/trust</b> - Trust score\n"
            f"\U0001F6A8 <b>/alerts</b> - Alert settings\n"
            f"\U0001F4CB <b>/summary</b> - Daily summary\n"
            f"\U0001F4E2 <b>/help</b> - Show this help\n"
        )
    
    def _get_pnl_command(self, args: List[str]) -> str:
        """Get P&L summary"""
        from risk_management import risk_manager
        
        portfolio = risk_manager.portfolio
        
        pnl = portfolio.total_unrealized_pnl
        pnl_str, pnl_emoji = self._format_pnl(pnl)
        pnl_pct = portfolio.total_unrealized_pnl_percent
        
        message = (
            f"\U0001F4B0 <b>P&L SUMMARY</b>\n\n"
            f"<b>Unrealized P&L:</b>\n"
            f"  {pnl_emoji} {pnl_str} ({pnl_pct:+.2f}%)\n\n"
            f"<b>Portfolio Value:</b> {self._format_price(portfolio.total_value)}\n"
            f"<b>Positions Value:</b> {self._format_price(portfolio.positions_value)}\n"
            f"<b>Cash:</b> {self._format_price(portfolio.cash)}\n"
        )
        
        if portfolio.positions:
            best_pnl = max((p.unrealized_pnl for p in portfolio.positions.values()), default=0)
            worst_pnl = min((p.unrealized_pnl for p in portfolio.positions.values()), default=0)
            
            message += (
                f"\n<b>Best Performer:</b> {self._format_price(best_pnl)}\n"
                f"<b>Worst Performer:</b> {self._format_price(worst_pnl)}"
            )
        
        return message
    
    def _get_summary_command(self, args: List[str]) -> str:
        """Get daily summary"""
        return self._get_status_command(args) + "\n\n" + self._get_pnl_command(args)
    
    def _get_alerts_command(self, args: List[str]) -> str:
        """Get alert settings"""
        message = (
            f"\U0001F6A8 <b>ALERT SETTINGS</b>\n\n"
            f"<b>Risk Thresholds:</b>\n"
            f"  Max Drawdown: {self.alert_thresholds['max_drawdown']:.1f}%\n"
            f"  Max Position Risk: {self.alert_thresholds['max_position_risk']:.1f}%\n"
            f"  Max Portfolio Risk: {self.alert_thresholds['max_portfolio_risk']:.1f}%\n\n"
            f"<b>Trust Thresholds:</b>\n"
            f"  Low Warning: {self.alert_thresholds['trust_score_low']:.1f}\n"
            f"  Critical: {self.alert_thresholds['trust_score_critical']:.1f}\n\n"
            f"<b>Rate Limiting:</b>\n"
            f"  Alert Cooldown: {self.alert_cooldown // 60} minutes\n\n"
            f"<b>Settings:</b>\n"
            f"Use /help for command list"
        )
        return message
    
    # ==================== NEW TRADING ENGINE COMMANDS ====================
    
    def _get_engine_command(self, args: List[str]) -> str:
        """Get trading engine status"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F916 <b>ENGINE STATUS</b>\n\nEngine not initialized.\nUse /start to initialize."
            
            status = engine.get_status()
            
            state_emoji = {
                "TRADING": "\U0001F7E2",
                "READY": "\U0001F7E1",
                "PAUSED": "\U0001F7E0",
                "STOPPED": "\U0001F534",
                "ERROR": "\U0001F534",
            }.get(status.state, "\u26AA")
            
            pnl_str, pnl_emoji = self._format_pnl(status.total_pnl)
            
            message = (
                f"\U0001F916 <b>ENGINE STATUS</b>\n\n"
                f"<b>State:</b> {state_emoji} {status.state}\n"
                f"<b>Balance:</b> {self._format_price(status.balance)}\n"
                f"<b>Leverage:</b> {status.leverage}x\n"
                f"<b>Positions:</b> {status.positions_count}\n\n"
                f"<b>Total P&L:</b> {pnl_emoji} {pnl_str}\n"
                f"<b>Daily P&L:</b> {status.daily_pnl_percent:+.2f}%\n"
                f"<b>Win Rate:</b> {status.win_rate:.1f}%\n"
                f"<b>Total Trades:</b> {status.total_trades}\n\n"
                f"<b>Market Regime:</b> {status.current_regime}\n"
                f"<b>Best Strategy:</b> {status.best_strategy}\n"
                f"<b>Kelly Fraction:</b> {status.kelly_fraction:.2%}\n"
                f"<b>VaR (95%):</b> ${status.var_95:.2f} ({status.var_95_percent:.2f}%)\n"
                f"<b>Risk Level:</b> {status.risk_level}\n"
                f"<b>Circuit Breaker:</b> {status.circuit_breaker_state}\n"
                f"<b>Can Trade:</b> {'YES' if status.can_trade else 'NO'}\n"
            )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ENGINE ERROR</b>\n\n{str(e)}"
    
    def _get_start_command(self, args: List[str]) -> str:
        """Start the trading engine"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            if engine.state.value == "TRADING":
                return "\U0001F7E2 Engine is already trading"
            
            success = engine.start()
            
            if success:
                return "\U0001F7E2 <b>ENGINE STARTED</b>\n\nTrading is now active"
            else:
                return f"\U0001F534 <b>ENGINE FAILED TO START</b>\n\nState: {engine.state.value}"
                
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_stop_command(self, args: List[str]) -> str:
        """Stop the trading engine"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            if engine.state.value == "STOPPED":
                return "\U0001F534 Engine is already stopped"
            
            engine.stop()
            return "\U0001F534 <b>ENGINE STOPPED</b>\n\nTrading has been halted"
                
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_leverage_command(self, args: List[str]) -> str:
        """Get or set leverage"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            # If args provided, try to set leverage
            if args:
                try:
                    new_leverage = int(args[0])
                    if 1 <= new_leverage <= 125:
                        success = engine.set_leverage(new_leverage)
                        if success:
                            return f"\u26A1 <b>LEVERAGE SET</b>\n\nNew leverage: <b>{new_leverage}x</b>"
                        else:
                            return "\U0001F6AB Failed to set leverage"
                    else:
                        return "\U0001F6AB Leverage must be between 1 and 125"
                except ValueError:
                    return "\U0001F6AB Invalid leverage value"
            
            # Show current leverage
            message = (
                f"\u26A1 <b>LEVERAGE</b>\n\n"
                f"<b>Current:</b> {engine.leverage}x\n"
                f"<b>Symbol:</b> {engine.symbol}\n\n"
                f"Usage: /leverage [number]\n"
                f"Example: /leverage 50"
            )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_kelly_command(self, args: List[str]) -> str:
        """Get Kelly Criterion statistics"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            stats = engine.kelly_sizer.get_statistics()
            
            edge = stats.get('edge', 'NO DATA')
            edge_emoji = {
                'STRONG': '\U0001F7E2',
                'MODERATE': '\U0001F7E1',
                'WEAK': '\U0001F7E0',
                'NO EDGE': '\U0001F534',
                'NO DATA': '\u26AA',
                'INSUFFICIENT DATA': '\u26AA',
            }.get(edge, '\u26AA')
            
            recommended_leverage = engine.kelly_sizer.get_recommended_leverage()
            
            message = (
                f"\U0001F3AF <b>KELLY CRITERION</b>\n\n"
                f"<b>Edge:</b> {edge_emoji} {edge}\n"
                f"<b>Kelly Fraction:</b> {stats.get('kelly_fraction', 0):.2%}\n"
                f"<b>Optimal (Half):</b> {stats.get('optimal_fraction', 0):.2%}\n"
                f"<b>Expected Growth:</b> {stats.get('expected_growth', 0):.4f}\n\n"
                f"<b>Trade Stats:</b>\n"
                f"  Total: {stats.get('trades_count', 0)}\n"
                f"  Wins: {stats.get('wins_count', 0)}\n"
                f"  Losses: {stats.get('losses_count', 0)}\n"
                f"  Win Rate: {stats.get('win_rate', 0):.1%}\n\n"
                f"<b>Recommended Leverage:</b> {recommended_leverage}x\n"
                f"<b>Portfolio Value:</b> {self._format_price(engine.current_balance)}\n"
            )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_strategies_command(self, args: List[str]) -> str:
        """Get strategy router status"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            signal_report = engine.get_signal_report()
            
            message = (
                f"\U0001F4CA <b>STRATEGY ROUTER</b>\n\n"
                f"<b>Market Regime:</b> {signal_report['regime']}\n"
                f"<b>Best Strategy:</b> {signal_report['best_strategy']}\n\n"
            )
            
            for name, data in signal_report.get('strategies', {}).items():
                if 'error' in data:
                    message += f"\u2022 <b>{name}:</b> Error\n"
                else:
                    signal = data.get('signal', 'N/A')
                    signal_emoji = {
                        'BUY': '\U0001F4C8',
                        'SELL': '\U0001F4C9',
                        'NEUTRAL': '\u2796',
                    }.get(signal, '\u2753')
                    message += f"{signal_emoji} <b>{name}:</b> {signal}\n"
                    if 'reason' in data:
                        message += f"  {data['reason']}\n"
                    message += "\n"
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_signal_command(self, args: List[str]) -> str:
        """Get current trading signal"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            signal_report = engine.get_signal_report()
            status = engine.get_status()
            
            # Determine overall signal
            best = signal_report.get('best_strategy', 'none')
            regime = signal_report.get('regime', 'UNKNOWN')
            
            # Get best strategy's signal
            strategies = signal_report.get('strategies', {})
            best_data = strategies.get(best, {})
            best_signal = best_data.get('signal', 'NEUTRAL')
            best_reason = best_data.get('reason', 'No data')
            
            signal_emoji = {
                'BUY': '\U0001F4C8',
                'SELL': '\U0001F4C9',
                'NEUTRAL': '\u2796',
            }.get(best_signal, '\u2753')
            
            message = (
                f"\U0001F3AF <b>CURRENT SIGNAL</b>\n\n"
                f"<b>Signal:</b> {signal_emoji} {best_signal}\n"
                f"<b>Strategy:</b> {best}\n"
                f"<b>Reason:</b> {best_reason}\n\n"
                f"<b>Market Regime:</b> {regime}\n"
                f"<b>Confidence:</b> {best_data.get('confidence', 0):.1%}\n"
                f"<b>Can Trade:</b> {'YES' if status.can_trade else 'NO'}\n"
                f"<b>Positions:</b> {status.positions_count}\n"
            )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_orders_command(self, args: List[str]) -> str:
        """Get open orders and positions"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            positions = engine.get_positions()
            
            if not positions:
                return (
                    f"\U0001F4CB <b>ORDERS & POSITIONS</b>\n\n"
                    f"No open positions or orders.\n"
                    f"Waiting for signals..."
                )
            
            message = f"\U0001F4CB <b>ORDERS & POSITIONS</b>\n\n"
            
            for symbol, pos in positions.items():
                side = pos['side']
                emoji = "\U0001F4C8" if side == "LONG" else "\U0001F4C9"
                
                message += (
                    f"{emoji} <b>{symbol}</b>\n"
                    f"  Side: {side}\n"
                    f"  Qty: {pos['quantity']:.6f}\n"
                    f"  Entry: {self._format_price(pos['entry_price'])}\n"
                    f"  SL: {self._format_price(pos['stop_loss'])}\n"
                    f"  TP: {self._format_price(pos['take_profit'])}\n"
                    f"  Strategy: {pos['strategy']}\n\n"
                )
            
            # Get order manager stats if available
            if engine.order_manager:
                stats = engine.order_manager.get_statistics()
                message += (
                    f"<b>Order Stats:</b>\n"
                    f"  Total: {stats['total_orders']}\n"
                    f"  Filled: {stats['filled_orders']}\n"
                    f"  Pending: {stats['pending_orders']}\n"
                    f"  Fill Rate: {stats['fill_rate']:.1%}\n"
                )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_var_command(self, args: List[str]) -> str:
        """Get Value at Risk report"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            risk_report = engine.get_risk_report()
            var_data = risk_report.get('var', {})
            
            if not var_data:
                return (
                    f"\U0001F4C8 <b>VALUE AT RISK</b>\n\n"
                    f"Insufficient data for VaR calculation.\n"
                    f"Need at least 10 trades."
                )
            
            risk_level = var_data.get('risk_level', 'UNKNOWN')
            risk_emoji = {
                'LOW': '\U0001F7E2',
                'MODERATE': '\U0001F7E1',
                'HIGH': '\U0001F7E0',
                'CRITICAL': '\U0001F534',
            }.get(risk_level, '\u26AA')
            
            message = (
                f"\U0001F4C8 <b>VALUE AT RISK</b>\n\n"
                f"<b>Risk Level:</b> {risk_emoji} {risk_level}\n\n"
                f"<b>VaR (95%):</b> ${var_data.get('var_95_dollars', 0):.2f}\n"
                f"  ({var_data.get('var_95_percent', 0):.2f}% of portfolio)\n\n"
                f"<b>VaR (99%):</b> ${var_data.get('var_99_dollars', 0):.2f}\n"
                f"  ({var_data.get('var_99_percent', 0):.2f}% of portfolio)\n\n"
                f"<b>CVaR (95%):</b> ${var_data.get('cvar_95', 0):.2f}\n"
                f"<b>CVaR (99%):</b> ${var_data.get('cvar_99', 0):.2f}\n\n"
                f"<b>Max Drawdown:</b> {var_data.get('max_drawdown_percent', 0):.2f}%\n"
                f"<b>Volatility:</b> {var_data.get('volatility_annualized', 0):.2f}%\n"
                f"<b>Method:</b> {var_data.get('method', 'N/A')}\n"
            )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"

    def _get_unknown_command(self, command: str) -> str:
        """Handle unknown commands"""
        return (
            f"\U0001F6AB <b>UNKNOWN COMMAND</b>\n\n"
            f"Command /{command} not recognized.\n"
            f"Send /help for available commands."
        )
    
    # ==================== SYSTEM NOTIFICATIONS ====================
    
    def send_startup_message(self) -> bool:
        """Send startup notification"""
        message = (
            f"{TelegramEmoji.ROBOT.value} <b>GOD MODE QUANT ORCHESTRATOR</b>\n\n"
            f"Trading system is now ONLINE\n\n"
            f"Monitoring and alerts active\n"
            f"Use /help for available commands\n\n"
            f"\U0001F4E2 Waiting for trades..."
        )
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "system", "status": "sent"}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    def send_shutdown_message(self) -> bool:
        """Send shutdown notification"""
        with self._lock:
            stats = self.daily_stats.copy()
        
        message = (
            f"\U0001F6D1 <b>SYSTEM SHUTDOWN</b>\n\n"
            f"Trading orchestrator is stopping\n\n"
            f"<b>Session Stats:</b>\n"
            f"  Trades: {stats.get('trades', 0)}\n"
            f"  P&L: {self._format_price(stats.get('pnl', 0))}\n\n"
            f"Thank you for using God Mode Quant!"
        )
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "system", "status": "sent"}
        )
        
        return self._send_message(message)
    
    def send_error_notification(self, error_message: str, context: Optional[Dict] = None) -> bool:
        """Send error notification"""
        message = (
            f"\U0001F6A8 <b>ERROR NOTIFICATION</b>\n\n"
            f"<b>Error:</b> {error_message}\n"
        )
        
        if context:
            message += "\n<b>Context:</b>\n"
            for key, value in context.items():
                message += f"  \u2022 {key}: {value}\n"
        
        message += f"\n\U000023F0 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "error", "status": "sent"}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    def send_heartbeat(self, status: str = "running") -> bool:
        """Send heartbeat/status update"""
        from risk_management import risk_manager
        from security.trust_scorer import trust_scorer
        
        portfolio = risk_manager.portfolio
        trust_score = trust_scorer.get_trust_score("orchestrator:system")
        
        pnl = portfolio.total_unrealized_pnl
        pnl_str, _ = self._format_pnl(pnl)
        
        message = (
            f"\U0001F525 <b>HEARTBEAT</b>\n\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Positions:</b> {portfolio.position_count}\n"
            f"<b>P&L:</b> {pnl_str}\n"
            f"<b>Trust:</b> {trust_score:.1f}\n"
            f"\U000023F0 {datetime.now().strftime('%H:%M:%S')}"
        )
        
        return self._send_message(message)


# Global dashboard instance
_dashboard_instance: Optional[TelegramDashboard] = None


def init_telegram_dashboard(bot_token: str = None, chat_id: str = None) -> TelegramDashboard:
    """Initialize the global Telegram dashboard"""
    global _dashboard_instance
    
    if bot_token is None:
        from security.secrets_manager import get_telegram_bot_token
        bot_token = get_telegram_bot_token() or os.getenv('TELEGRAM_BOT_TOKEN')
    
    if chat_id is None:
        from security.secrets_manager import get_telegram_chat_id
        chat_id = get_telegram_chat_id() or os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        raise ValueError("Telegram bot token and chat ID are required")
    
    _dashboard_instance = TelegramDashboard(bot_token, chat_id)
    logger.info("Telegram dashboard initialized")
    
    return _dashboard_instance


def get_telegram_dashboard() -> Optional[TelegramDashboard]:
    """Get the global dashboard instance"""
    return _dashboard_instance


# Convenience functions for common notifications
def send_trade_entry_notification(symbol: str, side: str, quantity: float,
                                 entry_price: float, strategy: str = "unknown",
                                 stop_loss: float = None, take_profit: float = None) -> bool:
    """Send trade entry notification"""
    dashboard = get_telegram_dashboard()
    if dashboard:
        trade = TradeNotification(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy
        )
        return dashboard.send_trade_entry(trade)
    return False


def send_trade_exit_notification(symbol: str, side: str, quantity: float,
                                 entry_price: float, exit_price: float,
                                 pnl: float = None, pnl_percent: float = None) -> bool:
    """Send trade exit notification"""
    dashboard = get_telegram_dashboard()
    if dashboard:
        trade = TradeNotification(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            current_price=exit_price,
            pnl=pnl,
            pnl_percent=pnl_percent
        )
        return dashboard.send_trade_exit(trade)
    return False


def send_risk_alert_notification(alert_type: str, severity: str, 
                                message: str, details: Dict = None) -> bool:
    """Send risk alert notification"""
    dashboard = get_telegram_dashboard()
    if dashboard:
        alert = RiskAlertNotification(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {}
        )
        return dashboard.send_risk_alert(alert)
    return False
