# Telegram Dashboard Guide

> Complete guide to the Telegram Dashboard and Bot features

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Features](#features)
- [Commands](#commands)
- [Inline Keyboards](#inline-keyboards)
- [Notifications](#notifications)
- [Python API](#python-api)
- [Configuration](#configuration)

## Overview

The Telegram Dashboard provides real-time trading monitoring and control through an interactive Telegram bot. It includes:

- **Trade Notifications**: Entry/exit alerts with P&L
- **Risk Alerts**: Drawdown and position limit warnings
- **Trust Monitoring**: Security posture notifications
- **Interactive Commands**: Status, positions, risk reports
- **Inline Keyboards**: Quick action buttons

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` to create a new bot
3. Follow the prompts to name your bot
4. Copy the **Bot Token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

1. Search for **@userinfobot**
2. Send `/start`
3. Copy your **Chat ID** (a number like `123456789`)

### 3. Configure Environment

Add to your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 4. Test the Setup

```bash
python test_telegram.py
```

You should receive a test message in your Telegram chat.

## Features

### Trade Notifications

Sent automatically when trades execute:

```
🚀 TRADE ENTRY

Symbol: BTCUSDT
Side: LONG
Quantity: 0.500000
Entry Price: 50,000.00
Strategy: ma_crossover_01
Stop Loss: 48,000.00
Take Profit: 55,000.00

⏰ 2026-03-26 12:00:00
```

### Risk Alerts

Alerts when risk thresholds are breached:

```
⚠️ RISK ALERT

Type: drawdown
Severity: HIGH

Message: Portfolio drawdown exceeds limit

Details:
  • current_drawdown: 12.50%
  • limit: 10.00%
  • portfolio_value: $87,500.00

⏰ 2026-03-26 12:00:00
```

### Trust Score Alerts

Notifications when trust score changes significantly:

```
🛑 TRUST SCORE CHANGE

Service: orchestrator:system
Old Score: 95.0
New Score: 85.0
Change: -10.0
Reason: Trust score updated

⚠️ Action Required: Trust score below threshold!
```

### Daily Summary

Automated daily reports:

```
📊 DAILY SUMMARY

Date: 2026-03-26
Time: 23:59:59

Trades: 15
  ✓ Profitable: 10
  ✗ Losing: 5
  🎯 Win Rate: 66.7%

P&L: 💰 +$1,250.00

Portfolio:
  Value: $101,250.00
  Positions: 3
  Unrealized P&L: $1,250.00
  Max Drawdown: 2.50%

🎯 Trust Score: 95.0

🔔 Next update at midnight
```

## Commands

### Available Commands

| Command | Description |
|---------|-------------|
| `/status` | Portfolio value, P&L, positions count, trust score |
| `/positions` | Detailed open positions with P&L |
| `/risk` | Risk report with limits and utilization |
| `/trust` | Trust score and status |
| `/pnl` | P&L summary |
| `/summary` | Combined status and P&L |
| `/alerts` | Current alert settings |
| `/help` | Help message with all commands |

### Usage Examples

#### `/status` Output
```
🤖 SYSTEM STATUS

Portfolio Value: $101,250.00
Unrealized P&L: 💰 +$1,250.00
Positions: 3
Cash: $25,000.00
Max Drawdown: 2.50%

🎯 Trust Score: 95.0

💰 Trading Active
```

#### `/positions` Output
```
📋 OPEN POSITIONS (3)

📈 BTCUSDT
  Side: LONG | Qty: 0.5000
  Entry: 50,000.00
  Current: 51,500.00
  P&L: 💰 +$750.00 (+1.50%)
  SL: 48,000.00 | TP: 55,000.00

📈 ETHUSDT
  Side: LONG | Qty: 2.0000
  Entry: 3,000.00
  Current: 3,200.00
  P&L: 💰 +$400.00 (+6.67%)

📇 SOLUSDT
  Side: SHORT | Qty: 10.0000
  Entry: 100.00
  Current: 98.00
  P&L: 💰 +$20.00 (+2.00%)
```

#### `/risk` Output
```
🛡️ RISK REPORT

Portfolio Risk: 3.50%
  Limit: 5.00%
  Utilization: 70.0%

Max Drawdown: 2.50%
  Limit: 10.00%

Position Limits:
  Max per position: 2.00%

💰 Risk OK
```

## Inline Keyboards

Quick action buttons below each message:

```
┌─────────────────────────────────────┐
│  📈 Status    │ 📊 Positions        │
│  🛡️ Risk     │ 🎯 Trust            │
│  💰 P&L      │ 📋 Summary          │
│  🔔 Alerts On │ ⛔️ Alerts Off       │
└─────────────────────────────────────┘
```

### Button Actions

| Button | Action |
|--------|--------|
| Status | Shows system status |
| Positions | Lists open positions |
| Risk | Shows risk report |
| Trust | Shows trust score |
| P&L | Shows P&L summary |
| Summary | Shows daily summary |
| Alerts On | Enables alerts |
| Alerts Off | Disables alerts |

## Notifications

### Notification Types

1. **Trade Entry**: New position opened
2. **Trade Exit**: Position closed with P&L
3. **Risk Alert**: Threshold breach
4. **Trust Change**: Score change alert
5. **Daily Summary**: End-of-day report
6. **Weekly Summary**: End-of-week report
7. **Heartbeat**: Periodic status update
8. **Error**: System errors

### Alert Thresholds (Configurable)

```python
alert_thresholds = {
    "max_drawdown": 10.0,          # 10% max drawdown
    "max_position_risk": 2.0,      # 2% per position
    "max_portfolio_risk": 5.0,     # 5% total portfolio
    "trust_score_low": 50.0,       # Alert if below 50
    "trust_score_critical": 30.0  # Critical if below 30
}
```

### Rate Limiting

Alerts are rate-limited to prevent spam:
- Default cooldown: 5 minutes between alerts of same type

## Python API

### Initialize Dashboard

```python
from telegram_dashboard import init_telegram_dashboard

dashboard = init_telegram_dashboard(
    bot_token="your_token",
    chat_id="your_chat_id"
)
```

### Send Trade Entry Notification

```python
from telegram_dashboard import send_trade_entry_notification

send_trade_entry_notification(
    symbol="BTCUSDT",
    side="LONG",
    quantity=0.5,
    entry_price=50000.0,
    strategy="ma_crossover_01",
    stop_loss=48000.0,
    take_profit=55000.0
)
```

### Send Trade Exit Notification

```python
from telegram_dashboard import send_trade_exit_notification

send_trade_exit_notification(
    symbol="BTCUSDT",
    side="LONG",
    quantity=0.5,
    entry_price=50000.0,
    exit_price=51500.0,
    pnl=750.0,
    pnl_percent=1.5
)
```

### Send Risk Alert

```python
from telegram_dashboard import send_risk_alert_notification

send_risk_alert_notification(
    alert_type="drawdown",
    severity="HIGH",
    message="Portfolio drawdown exceeds limit",
    details={
        "current_drawdown": "12.50%",
        "limit": "10.00%"
    }
)
```

### Manual Message Sending

```python
from telegram_dashboard import get_telegram_dashboard

dashboard = get_telegram_dashboard()
dashboard.send_startup_message()
dashboard.send_shutdown_message()
dashboard.send_heartbeat(status="running")
```

### Handle Commands

```python
from telegram_dashboard import get_telegram_dashboard

dashboard = get_telegram_dashboard()

# Process a command
response = dashboard.handle_command("status")
print(response)
```

## Configuration

### Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional - Dashboard settings
MAX_DRAWDOWN=10.0
MAX_POSITION_RISK=2.0
MAX_PORTFOLIO_RISK=5.0
TRUST_SCORE_LOW=50.0
TRUST_SCORE_CRITICAL=30.0
ALERT_COOLDOWN=300
```

### Dashboard Initialization Options

```python
dashboard = TelegramDashboard(
    bot_token="token",
    chat_id="chat_id",
    alert_thresholds={
        "max_drawdown": 10.0,
        "max_position_risk": 2.0,
        "max_portfolio_risk": 5.0,
        "trust_score_low": 50.0,
        "trust_score_critical": 30.0
    },
    alert_cooldown=300  # seconds
)
```

---

## Troubleshooting

### Bot Not Responding

1. Ensure bot token is correct
2. Start a chat with the bot (send `/start`)
3. Check logs for errors

### Messages Not Delivered

1. Verify chat ID is correct
2. Check network connectivity
3. Ensure bot hasn't been blocked

### Rate Limits

Telegram has rate limits. The dashboard includes:
- 5-minute cooldown between same-type alerts
- Batch message handling

---

**Related Documentation:**
- [README.md](README.md) - Main project documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [API.md](API.md) - API endpoints
