"""
Prometheus Metrics for God Mode Quant Trading Orchestrator
Provides helper functions to update metrics from trading system
"""
import logging

logger = logging.getLogger(__name__)

# Note: All Prometheus metrics are defined in telegram_dashboard.py
# to ensure proper registration in the default registry.

def update_trading_metrics(portfolio, risk_report=None):
    """Update trading metrics from portfolio data"""
    try:
        from telegram_dashboard import get_telegram_dashboard
        dashboard = get_telegram_dashboard()
        if dashboard and dashboard.active_positions_gauge:
            dashboard.active_positions_gauge.set(len(portfolio.positions) if hasattr(portfolio, 'positions') else 0)
        if dashboard and dashboard.pnl_gauge:
            pnl = getattr(portfolio, 'total_unrealized_pnl', 0)
            dashboard.pnl_gauge.set(pnl)
    except Exception as e:
        logger.debug(f"Could not update trading metrics: {e}")

def update_trust_metrics(trust_scores):
    """Update trust score metrics"""
    try:
        from telegram_dashboard import get_telegram_dashboard
        dashboard = get_telegram_dashboard()
        if dashboard and dashboard.trust_score_gauge:
            for service_or_user, score in trust_scores.items():
                dashboard.trust_score_gauge.set(score)
    except Exception as e:
        logger.debug(f"Could not update trust metrics: {e}")

def update_risk_metrics(risk_report):
    """Update risk metrics"""
    try:
        from telegram_dashboard import get_telegram_dashboard
        dashboard = get_telegram_dashboard()
        if dashboard and dashboard.risk_alert_count:
            if risk_report.get('risk_status', {}).get('should_stop_trading'):
                dashboard.risk_alert_count.labels(alert_type='trading_stop', severity='CRITICAL').inc()
    except Exception as e:
        logger.debug(f"Could not update risk metrics: {e}")
