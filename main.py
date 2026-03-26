import os
import sys
import time
import requests
import ssl
import logging
from threading import Thread
from flask import Flask, jsonify
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app for health checks
app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "god-mode-quant-orchestrator"})

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    # Import metrics from the metrics module
    try:
        from metrics import (
            update_trading_metrics, update_trust_metrics
        )
        
        # Update metrics from current state
        try:
            from risk_management import risk_manager
            update_trading_metrics(risk_manager.portfolio)
        except Exception:
            pass
        
        try:
            from security.trust_scorer import trust_scorer
            score = trust_scorer.get_trust_score("orchestrator:system")
            update_trust_metrics({"orchestrator:system": score})
        except Exception:
            pass
            
    except ImportError:
        pass
    
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def run_health_server():
    """Run health server on port 8003"""
    app.run(host='0.0.0.0', port=8003, debug=False, use_reloader=False, threaded=True)

# Legacy function for backward compatibility
def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram notification sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False

def main():
    print("=== GOD MODE QUANT TRADING ORCHESTRATOR STARTING ===")
    
    # Initialize security components
    from security.mtls_manager import mtls_manager
    from security.secrets_manager import get_binance_api_key, get_binance_api_secret, get_telegram_bot_token, get_telegram_chat_id
    
    # Get environment variables (with fallback to secrets manager)
    telegram_token = get_telegram_bot_token() or os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id = get_telegram_chat_id() or os.getenv('TELEGRAM_CHAT_ID', '')
    
    print(f"Environment check:")
    print(f"  TELEGRAM_BOT_TOKEN: {'SET' if telegram_token else 'NOT SET'}")
    print(f"  TELEGRAM_CHAT_ID: {'SET' if telegram_chat_id else 'NOT SET'}")
    
    if not telegram_token or not telegram_chat_id:
        print("Telegram credentials not configured")
        # Try loading from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
            telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            print(f"Loaded from .env - TOKEN: {'SET' if telegram_token else 'NOT SET'}, CHAT_ID: {'SET' if telegram_chat_id else 'NOT SET'}")
        except ImportError:
            pass
        
        if not telegram_token or not telegram_chat_id:
            print("Telegram credentials not configured - exiting")
            sys.exit(1)
    
    # Try to import vnpy to ensure it's installed
    vnpy_available = False
    try:
        import vnpy
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        from vnpy_ctastrategy import CtaStrategyApp
        print(f"VNPY imported successfully: {vnpy.__version__}")
        vnpy_available = True
    except ImportError as e:
        print(f"VNPY not available: {e}")
        print("Running in DEMO/MOCK mode - no live trading")
        vnpy_available = False
    
    # ============================================================
    # ENHANCED TELEGRAM DASHBOARD INITIALIZATION
    # ============================================================
    print("\n=== Initializing Telegram Dashboard ===")
    try:
        from telegram_dashboard import init_telegram_dashboard, get_telegram_dashboard
        from telegram_bot_handler import init_telegram_bot
        
        # Initialize the enhanced Telegram dashboard
        dashboard = init_telegram_dashboard(telegram_token, telegram_chat_id)
        print("Enhanced Telegram Dashboard initialized successfully")
        
        # Initialize Telegram bot handler for commands (pass dashboard directly)
        bot_handler = init_telegram_bot(telegram_token, dashboard=dashboard)
        print("Telegram Bot Handler initialized successfully")
        
        # Start polling in a background thread
        polling_thread = Thread(target=bot_handler.start_polling, daemon=True)
        polling_thread.start()
        print("Telegram polling started in background")
        
        # Send startup message via enhanced dashboard
        dashboard.send_startup_message()
        
    except Exception as e:
        print(f"Failed to initialize Telegram Dashboard: {e}")
        print("Warning: Continuing with basic notifications only")
        dashboard = None
        bot_handler = None
    
    # ============================================================
    # PROMETHEUS METRICS SERVER STARTUP
    # ============================================================
    try:
        from prometheus_client import start_http_server
        # Start metrics server on port 9090
        metrics_thread = Thread(target=start_http_server, args=(9090,), daemon=True)
        metrics_thread.start()
        print("Prometheus metrics server started on port 9090")
    except ImportError:
        print("Warning: prometheus_client not available, metrics disabled")
    except Exception as e:
        print(f"Failed to start metrics server: {e}")
    
    # Send startup notification
    message = "<b>God Mode Quant Trading Orchestrator</b> is now running with vnpy backbone."
    print(f"Attempting to send Telegram notification...")
    result = send_telegram_message(telegram_token, telegram_chat_id, message)
    print(f"Telegram notification result: {result}")
    
    # Initialize audit logger
    print("Initializing Audit Logger...")
    try:
        from security.audit_logger import log_security_event
        # Log startup event
        log_security_event(
            service="orchestrator",
            user="system",
            action="startup",
            outcome="success",
            details={"version": "1.0.0", "component": "main_orchestrator"}
        )
        print("Audit Logger initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Audit Logger: {e}")
        print("Warning: Continuing without audit logging")
    
    # Initialize trust scorer
    print("Initializing Trust Scorer...")
    try:
        from security.trust_scorer import record_trust_event, get_trust_score, TrustEventType
        # Record startup event for trust scoring
        record_trust_event(
            service_or_user="orchestrator:system",
            event_type=TrustEventType.AUTH_SUCCESS,
            service="orchestrator",
            user="system",
            description="Orchestrator startup",
            metadata={"version": "1.0.0", "component": "main_orchestrator"}
        )
        initial_score = get_trust_score("orchestrator:system")
        print(f"Trust Scorer initialized successfully (initial score: {initial_score:.1f})")
    except Exception as e:
        print(f"Failed to initialize Trust Scorer: {e}")
        print("Warning: Continuing without trust scoring")
    
    # Initialize risk manager
    print("Initializing Risk Manager...")
    try:
        from risk_management import risk_manager, update_portfolio_value
        # Initialize with starting portfolio value
        update_portfolio_value(100000.0)  # Starting with $100,000 portfolio
        print("Risk Manager initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Risk Manager: {e}")
        print("Warning: Continuing without risk management")
    
    # Initialize vnpy trading system (only if available)
    cta_engine = None
    if vnpy_available:
        print("Initializing vnpy trading system...")
        try:
            # Create event engine
            event_engine = EventEngine()
            
            # Create main engine
            main_engine = MainEngine(event_engine)
            
            # Add CTA strategy app
            cta_engine = main_engine.add_app(CtaStrategyApp)
            
            # Load strategy setting (empty for now)
            strategy_setting = {}
            
            # Add our MA crossover strategy
            try:
                cta_engine.add_strategy(
                    class_name="MaCrossoverStrategy",
                    strategy_name="ma_crossover_01",
                    vt_symbol="BINANCE:BTCUSDT",  # Example symbol
                    setting=strategy_setting
                )
                print("MA Crossover strategy added successfully")
            except Exception as e:
                print(f"Failed to add strategy: {e}")
            
            # Initialize all strategies
            cta_engine.init_all_strategies()
            print("All strategies initialized")
            
            # Start all strategies
            cta_engine.start_all_strategies()
            print("All strategies started")
        except Exception as e:
            print(f"Failed to initialize vnpy trading system: {e}")
            print("Continuing in DEMO mode")
            vnpy_available = False
    else:
        print("Running in DEMO mode - no live trading engine")
    
    # Start health check server in background thread
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    print("Health check server started on port 8000")
    
    # Send strategy start notification
    strategy_message = "<b>MA Crossover Strategy</b> has been started on BINANCE:BTCUSDT"
    send_telegram_message(telegram_token, telegram_chat_id, strategy_message)
    
    # Keep the orchestrator running for a limited time for testing
    print("Trading orchestrator started. Entering main loop...")
    
    # Track last summary sent times
    last_daily_summary = datetime.now()
    last_weekly_summary = datetime.now()
    
    try:
        counter = 0
        max_iterations = 3  # For testing, run only 3 iterations
        while counter < max_iterations:
            time.sleep(5)  # Sleep for 5 seconds for testing
            counter += 1
            print(f"Heartbeat: Orchestrator running... ({counter * 5}s)", flush=True)
            
            # Periodic status update every 2 iterations (10 seconds) for testing
            if counter % 2 == 0:
                # Use enhanced dashboard if available
                if dashboard:
                    dashboard.send_heartbeat()
                else:
                    status_message = f"<b>God Mode Quant Trading Orchestrator</b> is running normally. Strategies active: {len(cta_engine.strategies)}"
                    send_telegram_message(telegram_token, telegram_chat_id, status_message)
                
                # Check risk limits and send alerts
                if dashboard:
                    from risk_management import risk_manager
                    from security.trust_scorer import trust_scorer
                    
                    # Check drawdown
                    should_stop, reasons = risk_manager.should_stop_trading()
                    if should_stop:
                        from telegram_dashboard import RiskAlertNotification
                        for reason in reasons:
                            alert = RiskAlertNotification(
                                alert_type="risk_limit_breach",
                                severity="CRITICAL",
                                message=reason
                            )
                            dashboard.send_risk_alert(alert)
                    
                    # Check trust score changes
                    trust_score = trust_scorer.get_trust_score("orchestrator:system")
                    dashboard.check_trust_score_change("orchestrator:system", trust_score)
    except KeyboardInterrupt:
        print("\nShutting down...")
        # Stop all strategies
        cta_engine.stop_all_strategies()
        print("All strategies stopped")
        
        # Send shutdown notification via enhanced dashboard
        if dashboard:
            dashboard.send_shutdown_message()
        else:
            shutdown_message = "<b>God Mode Quant Trading Orchestrator</b> is shutting down."
            send_telegram_message(telegram_token, telegram_chat_id, shutdown_message)

if __name__ == "__main__":
    main()
