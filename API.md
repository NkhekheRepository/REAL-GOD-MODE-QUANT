# API Reference

> Complete API documentation for the God Mode Quant Trading Orchestrator

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Metrics](#metrics)
  - [Telegram Webhook](#telegram-webhook)
- [WebSocket](#websocket)
- [Error Codes](#error-codes)

## Overview

The God Mode Quant Trading Orchestrator exposes a RESTful API for:

- Health monitoring
- Prometheus metrics exposition
- Telegram bot webhook handling

## Base URL

| Environment | URL |
|-------------|-----|
| Development | http://localhost:8000 |
| Production | https://api.yourdomain.com |

## Authentication

Currently, the API does not require authentication for health and metrics endpoints.

> **Note**: For production, add API key authentication or JWT tokens.

## Endpoints

### Health

Check orchestrator health status.

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "god-mode-quant-orchestrator"
}
```

**cURL:**
```bash
curl http://localhost:8000/health
```

---

### Metrics

Get Prometheus metrics in OpenMetrics format.

```
GET /metrics
```

**Response:**
```
# HELP telegram_messages_sent_total Total Telegram messages sent
# TYPE telegram_messages_sent_total counter
telegram_messages_sent_total{message_type="trade_entry",status="sent"} 42.0
telegram_messages_sent_total{message_type="trade_exit",status="sent"} 38.0

# HELP trading_active_positions Current number of active positions
# TYPE trading_active_positions gauge
trading_active_positions 3.0

# HELP trading_unrealized_pnl_dollars Unrealized P&L in dollars
# TYPE trading_unrealized_pnl_dollars gauge
trading_unrealized_pnl_dollars 1250.50

# HELP security_trust_score Current trust score
# TYPE security_trust_score gauge
security_trust_score{service_or_user="orchestrator:system"} 95.0
```

**cURL:**
```bash
curl http://localhost:8000/metrics
```

**Available Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `telegram_messages_sent_total` | Counter | message_type, status | Telegram messages sent |
| `telegram_last_message_time` | Gauge | message_type | Last message timestamp |
| `telegram_commands_received_total` | Counter | command | Commands received |
| `trading_active_positions` | Gauge | - | Active positions count |
| `trading_unrealized_pnl_dollars` | Gauge | - | Unrealized P&L |
| `trading_portfolio_value_dollars` | Gauge | - | Portfolio value |
| `trading_max_drawdown_percent` | Gauge | - | Max drawdown % |
| `security_trust_score` | Gauge | service_or_user | Trust score |
| `risk_alerts_triggered_total` | Counter | alert_type, severity | Risk alerts |
| `orchestrator_status` | Gauge | - | 1=running, 0=stopped |

---

### Telegram Webhook

Receive Telegram bot updates.

```
POST /webhook
```

**Request Body:**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "User"
    },
    "chat": {
      "id": 123456789,
      "type": "private"
    },
    "text": "/status",
    "date": 1234567890
  }
}
```

**Response:**
```json
{
  "ok": true
}
```

**Callback Query (Inline Button):**
```json
{
  "update_id": 123456789,
  "callback_query": {
    "id": "abc123",
    "from": {
      "id": 123456789,
      "first_name": "User"
    },
    "message": {
      "message_id": 1,
      "chat": {
        "id": 123456789
      }
    },
    "data": "cmd_status"
  }
}
```

---

### Bot Health (Telegram Bot Handler)

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "telegram-bot-handler"
}
```

---

## WebSocket

Currently not implemented. Future versions will include:

- Real-time position updates
- Trade execution notifications
- Risk alert streaming

---

## Error Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request format |
| 404 | Not Found | Endpoint not found |
| 500 | Internal Error | Server error |

### Error Response Format

```json
{
  "ok": false,
  "error": "Invalid request",
  "details": {
    "field": "message",
    "issue": "Missing required field"
  }
}
```

---

## Telegram Bot Commands

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/status` | Portfolio and system status | `/status` |
| `/positions` | Open positions | `/positions` |
| `/risk` | Risk report | `/risk` |
| `/trust` | Trust score | `/trust` |
| `/pnl` | P&L summary | `/pnl` |
| `/summary` | Daily summary | `/summary` |
| `/alerts` | Alert settings | `/alerts` |
| `/help` | Help message | `/help` |

### Inline Keyboard Buttons

| Button | Callback Data | Action |
|--------|--------------|--------|
| Status | `cmd_status` | Get system status |
| Positions | `cmd_positions` | Get open positions |
| Risk | `cmd_risk` | Get risk report |
| Trust | `cmd_trust` | Get trust score |
| P&L | `cmd_pnl` | Get P&L summary |
| Summary | `cmd_summary` | Get daily summary |
| Alerts On | `alerts_on` | Enable alerts |
| Alerts Off | `alerts_off` | Disable alerts |

---

## Python API Usage

### Sending Trade Notifications

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

### Sending Risk Alerts

```python
from telegram_dashboard import send_risk_alert_notification

send_risk_alert_notification(
    alert_type="drawdown",
    severity="HIGH",
    message="Portfolio drawdown exceeds 8%",
    details={"current_drawdown": "8.5%", "limit": "10%"}
)
```

### Trust Score Operations

```python
from security.trust_scorer import (
    record_trust_event,
    get_trust_score,
    get_trust_report,
    TrustEventType
)

# Record an event
record_trust_event(
    service_or_user="orchestrator:system",
    event_type=TrustEventType.AUTH_SUCCESS,
    service="orchestrator",
    user="system",
    description="Successful login"
)

# Get current score
score = get_trust_score("orchestrator:system")

# Get detailed report
report = get_trust_report("orchestrator:system")
```

### Audit Logging

```python
from security.audit_logger import (
    log_security_event,
    log_trade_event,
    log_auth_event
)

log_security_event(
    service="orchestrator",
    user="system",
    action="config_change",
    outcome="success",
    details={"key": "max_position_size", "old": 100, "new": 150}
)
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/health` | 60 req/min |
| `/metrics` | 60 req/min |
| `/webhook` | Telegram rate limits |

---

## Related Documentation

- [README.md](README.md) - Main project documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [TELEGRAM_DASHBOARD.md](TELEGRAM_DASHBOARD.md) - Telegram bot guide
