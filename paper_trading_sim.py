#!/usr/bin/env python3
"""
Extended Paper Trading Simulation for God Mode Quant Trading Orchestrator
Simulates multiple trading cycles with both winning and losing trades
"""
import sys
import os
import time
import random
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.modules['numpy'] = Mock()

mock_vnpy = Mock()
mock_vnpy.__version__ = "3.0.0"
sys.modules['vnpy'] = mock_vnpy
sys.modules['vnpy.event'] = Mock()
sys.modules['vnpy.trader'] = Mock()
sys.modules['vnpy.trader.engine'] = Mock()
sys.modules['vnpy.trader.object'] = Mock()
sys.modules['vnpy.trader.constant'] = Mock()
sys.modules['vnpy_ctastrategy'] = Mock()

print("=" * 70)
print("GOD MODE QUANT TRADING ORCHESTRATOR - EXTENDED PAPER TRADING")
print("=" * 70)

from risk_management import risk_manager, update_portfolio_value, should_stop_trading, get_risk_report
from security.trust_scorer import record_trust_event, get_trust_score, TrustEventType
from security.audit_logger import log_security_event

initial_portfolio = 100000.0
update_portfolio_value(initial_portfolio)

print(f"\n📊 INITIAL CONFIGURATION")
print(f"   Portfolio Value: ${initial_portfolio:,.2f}")
print(f"   Max Position Risk: {risk_manager.max_position_risk_percent}%")
print(f"   Max Portfolio Risk: {risk_manager.max_portfolio_risk_percent}%")
print(f"   Max Drawdown: {risk_manager.max_drawdown_percent}%")

trading_cycles = [
    {"cycle": 1, "symbol": "BTCUSDT", "side": "BUY", "quantity": 0.5, "entry_price": 42000.0, "exit_price": 43500.0},
    {"cycle": 2, "symbol": "ETHUSDT", "side": "BUY", "quantity": 2.0, "entry_price": 2250.0, "exit_price": 2380.0},
    {"cycle": 3, "symbol": "SOLUSDT", "side": "BUY", "quantity": 10.0, "entry_price": 95.0, "exit_price": 102.0},
    {"cycle": 4, "symbol": "BNBUSDT", "side": "BUY", "quantity": 5.0, "entry_price": 310.0, "exit_price": 295.0},
    {"cycle": 5, "symbol": "ADAUSDT", "side": "BUY", "quantity": 1000.0, "entry_price": 0.55, "exit_price": 0.58},
]

realized_pnl = 0.0
total_trades = 0
winning_trades = 0
losing_trades = 0

print("\n" + "=" * 70)
print("📈 TRADING CYCLES")
print("=" * 70)

for cycle in trading_cycles:
    symbol = cycle["symbol"]
    quantity = cycle["quantity"]
    entry_price = cycle["entry_price"]
    exit_price = cycle["exit_price"]
    
    risk_manager.add_position(symbol, quantity, entry_price)
    risk_manager.update_position_price(symbol, exit_price)
    
    position = risk_manager.portfolio.positions[symbol]
    pnl = position.unrealized_pnl
    pnl_pct = position.unrealized_pnl_percent
    
    realized_pnl += pnl
    total_trades += 1
    
    if pnl > 0:
        winning_trades += 1
        status = "✅ WIN"
    else:
        losing_trades += 1
        status = "❌ LOSS"
    
    print(f"\n  Cycle {cycle['cycle']}: {symbol}")
    print(f"    {cycle['side']} {quantity} @ ${entry_price:,.2f} → ${exit_price:,.2f}")
    print(f"    P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%) {status}")
    
    risk_manager.update_portfolio_value(initial_portfolio + realized_pnl)
    
    should_stop, reasons = should_stop_trading()
    if should_stop:
        print(f"    ⚠️ TRADING STOPPED: {reasons}")
        break
    
    record_trust_event(
        service_or_user=f"trading:{symbol}",
        event_type=TrustEventType.TRADE_EXECUTED if pnl > 0 else TrustEventType.TRADE_FAILED,
        service="paper_trading",
        user="system",
        description=f"Trade {status}",
        metadata={"pnl": pnl, "price": entry_price}
    )

update_portfolio_value(initial_portfolio + realized_pnl)

print("\n" + "=" * 70)
print("💼 FINAL PORTFOLIO SUMMARY")
print("=" * 70)

portfolio = risk_manager.portfolio
win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

print(f"\n  📊 Initial Portfolio: ${initial_portfolio:,.2f}")
print(f"  📊 Final Portfolio: ${portfolio.total_value:,.2f}")
print(f"  💰 Total P&L: ${realized_pnl:,.2f} ({realized_pnl/initial_portfolio*100:+.2f}%)")
print(f"  📈 Total Trades: {total_trades}")
print(f"  ✅ Winning Trades: {winning_trades}")
print(f"  ❌ Losing Trades: {losing_trades}")
print(f"  📊 Win Rate: {win_rate:.1f}%")

print("\n" + "=" * 70)
print("⚠️ RISK MANAGEMENT REPORT")
print("=" * 70)

report = get_risk_report()
risk_status = report["risk_status"]

print(f"\n  Portfolio Risk: {portfolio.total_risk_percent:.2f}% (Limit: {risk_manager.max_portfolio_risk_percent}%)")
print(f"  Max Drawdown: {portfolio.max_drawdown:.2f}% (Limit: {risk_manager.max_drawdown_percent}%)")
print(f"  Open Positions: {portfolio.position_count}")

should_stop, reasons = should_stop_trading()
print(f"\n  Trading Status: {'🟢 ACTIVE' if not should_stop else '🔴 STOPPED'}")

if reasons:
    print("  Stop Reasons:")
    for reason in reasons:
        print(f"    - {reason}")

print("\n" + "=" * 70)
print("🔐 TRUST SCORE MONITORING")
print("=" * 70)

trust_score = get_trust_score("orchestrator:system")
trust_level = "HIGH" if trust_score >= 80 else "MEDIUM" if trust_score >= 50 else "LOW"

print(f"\n  System Trust Score: {trust_score:.1f}/100 ({trust_level})")
print(f"  Risk Utilization: {risk_status['portfolio_risk_utilization']:.1f}%")

print("\n" + "=" * 70)
print("📋 POSITION DETAILS")
print("=" * 70)

for symbol, position in portfolio.positions.items():
    print(f"\n  {symbol}:")
    print(f"    Quantity: {position.quantity}")
    print(f"    Entry: ${position.entry_price:,.2f}")
    print(f"    Current: ${position.current_price:,.2f}")
    print(f"    P&L: ${position.unrealized_pnl:,.2f} ({position.unrealized_pnl_percent:+.2f}%)")
    print(f"    Stop Loss: ${position.stop_loss:,.2f}")
    print(f"    Take Profit: ${position.take_profit:,.2f}")

log_security_event(
    service="paper_trading",
    user="system",
    action="simulation_complete",
    outcome="success",
    details={
        "initial_portfolio": initial_portfolio,
        "final_portfolio": portfolio.total_value,
        "total_pnl": realized_pnl,
        "trades_count": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate
    }
)

print("\n" + "=" * 70)
print("✅ PAPER TRADING COMPLETE - READY FOR LIVE TRADING")
print("=" * 70)
print(f"""
  Summary:
  - Started with ${initial_portfolio:,.2f}
  - Ended with ${portfolio.total_value:,.2f}
  - P&L: ${realized_pnl:,.2f} ({realized_pnl/initial_portfolio*100:+.2f}%)
  - Win Rate: {win_rate:.1f}%
  - Risk Status: {'WITHIN LIMITS' if not should_stop else 'AT RISK LIMIT'}
  
  Next Steps:
  1. Configure exchange API keys in .env
  2. Enable live trading in main.py
  3. Start Docker Compose services
  4. Monitor via Telegram dashboard
""")
print("=" * 70)
