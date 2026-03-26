# GodMode Quant Orchestrator - Complete GitHub Documentation

*The all-in-one production-ready quantitative trading platform with VnPy backbone*

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [VnPy Backbone Architecture](#vnpy-backbone-architecture)
3. [System Architecture](#system-architecture)
4. [Quick Start](#quick-start)
5. [Installation Guide](#installation-guide)
6. [Configuration](#configuration)
7. [How It Works](#how-it-works)
8. [API Reference](#api-reference)
9. [Running & Managing](#running--managing)
10. [Monitoring & Observability](#monitoring--observability)
11. [Security Framework](#security-framework)
12. [Risk Management](#risk-management)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)
15. [License & Support](#license--support)

---

## 1. Project Overview

**GodMode Quant Orchestrator (GMQO)** is a production-grade, autonomous trading platform built on the **VnPy 3.9.4** framework. It provides a complete ecosystem for algorithmic trading with:

- ✅ **VnPy Core**: Industry-standard quantitative trading framework
- ✅ **Containerized Deployment**: Docker Compose for reproducible environments
- ✅ **Telegram Integration**: Real-time notifications and control
- ✅ **Security**: mTLS, audit logging, trust scoring
- ✅ **Monitoring**: Prometheus + Grafana out of the box
- ✅ **Risk Management**: Position limits, drawdown protection
- ✅ **ML Services**: Time series forecasting and sentiment analysis

### Why VnPy?

VnPy (VeighNa) is the most popular open-source Python trading framework with:

- **Event-Driven Architecture**: Asynchronous message bus (EventEngine) for high performance
- **Gateway Abstraction**: Unified interface to multiple exchanges (Binance, IB, CTP, etc.)
- **CTA Strategy Engine**: Built-in strategy development framework with backtesting
- **Production Ready**: Used by thousands of quant funds and traders worldwide
- **Active Community**: Continuous development and extensive documentation

---

## 2. VnPy Backbone Architecture

### 2.1 Core Components

```python
"""
VnPy Architecture - The Foundation
"""

# Event Engine - Central Message Bus
from vnpy.event import EventEngine, Event
# Handles all async communication between components

# Main Engine - Orchestration Core
from vnpy.trader.engine import MainEngine
# Manages gateways, strategies, risk, and data

# CTA Engine - Strategy Execution
from vnpy_ctastrategy import CtaStrategyApp, CtaTemplate
# Base classes for algorithmic strategies

# Gateway Interface - Exchange Connectivity
from vnpy.trader.gateway import BaseGateway
# Abstract interface for exchange APIs (Binance, IB, etc.)
```

### 2.2 VnPy Component Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                    VnPy Framework                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │           MainEngine (Central Hub)               │  │
│  │  - EventEngine (Message Bus)                     │  │
│  │  - OmsEngine (Order Management)                  │  │
│  │  - EmailEngine                                   │  │
│  │  - DatabaseEngine                                │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                               │
│         ┌────────────────┼────────────────┐             │
│         │                │                │             │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐    │
│  │   Gateway   │  │   Strategy  │  │    Risk    │    │
│  │  (Exchange) │  │   Engine    │  │  Manager   │    │
│  └─────────────┘  └─────────────┘  └────────────┘    │
│         │                │                │             │
│         ▼                ▼                ▼             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │
│  │ Market Data │ │   CTA       │ │  Position   │    │
│  │  Stream     │ │ Strategies  │ │   Limits    │    │
│  └─────────────┘ └─────────────┘ └─────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 2.3 VnPy Data Flow in GMQO

```
External Exchange (Binance)
         │
         ▼
┌─────────────────────┐
│   BinanceGateway    │  ← VnPy Gateway
│  (vnpy_binance)     │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│     EventEngine     │  ← VnPy Event Bus
│  (Async Message Bus)│
└─────────────────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Strategy  │ │   Risk      │ │   Position  │
│   Engine    │ │  Manager    │ │  Tracker    │
└─────────────┘ └─────────────┘ └─────────────┘
         │              │              │
         └──────────────┼──────────────┘
                        ▼
               ┌─────────────────┐
               │   PostgreSQL    │  ← Persistent Storage
               └─────────────────┘
```

---

## 3. System Architecture

### 3.1 Complete Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     GOD MODE QUANT ORCHESTRATOR                           │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐       │
│  │  Telegram     │      │   Trading     │      │   Security    │       │
│  │  Dashboard    │◄────►│   Engine      │◄────►│   Framework   │       │
│  │  (Bot + UI)   │      │  (VnPy 3.9.4) │      │               │       │
│  └───────────────┘      └───────────────┘      └───────────────┘       │
│         │                     │                     │                    │
│         └─────────────────────┼─────────────────────┘                    │
│                               │                                          │
│  ┌────────────────────────────▼──────────────────────────────────────┐  │
│  │                        Flask API Layer                            │  │
│  │  /health  /metrics  /webhook  /status  /positions  /risk         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                               │                                          │
├───────────────────────────────┼──────────────────────────────────────────┤
│                               ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                       INFRASTRUCTURE LAYER                         ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │  │ PostgreSQL  │  │    Redis    │  │ Prometheus │  │  Grafana    ││
│  │  │  (Port 5433)│  │  (Port 6380)│  │ (Port 9090)│  │ (Port 3000) ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                       ML SERVICES LAYER                            ││
│  │  ┌────────────────────────┐    ┌────────────────────────┐         ││
│  │  │ Time Series Forecast  │    │  Sentiment Analysis    │         ││
│  │  │ (Random Forest)        │    │  (NLP)                 │         ││
│  │  └────────────────────────┘    └────────────────────────┘         ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Details

| Component | Technology | Port | Purpose |
|-----------|------------|------|---------|
| **Trading Orchestrator** | Python + VnPy | 8000 | Main trading engine with Flask API |
| **PostgreSQL** | Postgres 16 | 5433 | Persistent storage for trades, strategies |
| **Redis** | Redis 7 | 6380 | Real-time caching, pub/sub, queues |
| **Prometheus** | Prometheus | 9090 | Metrics collection |
| **Grafana** | Grafana | 3000 | Visualization and dashboards |
| **ML Time Series** | FastAPI + Scikit-learn | 8001 | Price forecasting |
| **ML Sentiment** | FastAPI + NLP | 8002 | Market sentiment analysis |

---

## 4. Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Telegram Bot Token (see below)

### 5-Minute Setup

```bash
# 1. Clone repository
git clone https://github.com/NkhekheRepository/godmode-quant-orchestrator.git
cd godmode-quant-orchestrator

# 2. Configure environment
cp .env.example .env
# Edit .env and add your Telegram bot token and chat ID

# 3. Start all services
docker-compose up -d

# 4. Verify everything is running
docker-compose ps
curl http://localhost:8000/health  # Should return {"status":"healthy"}

# 5. Access dashboards
# - Trading API: http://localhost:8000
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090

# 6. Start your Telegram bot and send /start
```

That's it! You now have a complete autonomous trading platform running.

---

## 5. Installation Guide

### 5.1 Docker Deployment (Recommended)

The **docker-compose.yml** orchestrates all services:

```yaml
version: '3.8'

services:
  trading-orchestrator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    ports:
      - "5433:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-vnpy}

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    command: redis-server --requirepass ${REDIS_PASSWORD:-}

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}

  ml-time-series-forecast:
    build:
      context: .
      dockerfile: Dockerfile.ml
    environment:
      - MODEL_TYPE=random_forest
    volumes:
      - ./ai_ml:/app/ai_ml

  ml-sentiment-analysis:
    build:
      context: .
      dockerfile: Dockerfile.ml
    environment:
      - MODEL_TYPE=sentiment
```

### 5.2 Local Development (Alternative)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate (Windows)

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from vnpy.trader.database import init_database; init_database()"

# Run the orchestrator
python main.py
```

---

## 6. Configuration

### 6.1 Environment Variables (.env)

Create a `.env` file in the project root:

```dotenv
# Required
TELEGRAM_BOT_TOKEN=8766433670:AAGZzgTLrN09dYWsA-jbyVy5AKr423xxbgg
TELEGRAM_CHAT_ID=7361240735

# Database (defaults provided)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=vnpy

# Redis (optional password)
REDIS_PASSWORD=

# Trading Configuration
STARTING_CAPITAL=10
MAX_LEVERAGE=75
DAILY_LOSS_LIMIT=3
DEFAULT_STOP_LOSS=1.5
DEFAULT_TAKE_PROFIT=4
TRADING_SYMBOL=BTCUSDT
TRADING_INTERVAL=5

# Monitoring
GRAFANA_PASSWORD=admin

# Binance API (for real trading)
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_TESTNET=true
```

### 6.2 Telegram Bot Setup

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "GodMode Quant Bot")
4. Choose a username (must end in `_bot`)
5. BotFather will give you a **token** (e.g., `1234567890:ABCdef...`)
6. Add this token to your `.env` file as `TELEGRAM_BOT_TOKEN`

To get your **Chat ID**:
1. Open Telegram and search for **@userinfobot**
2. Send `/start` and it will reply with your chat ID
3. Add this ID to your `.env` file as `TELEGRAM_CHAT_ID`

---

## 7. How It Works

### 7.1 VnPy Integration Deep Dive

The GodMode Quant Orchestrator uses VnPy as its core trading engine:

```python
# Simplified initialization
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

# 1. Create event engine (message bus)
event_engine = EventEngine()

# 2. Create main engine (orchestrator)
main_engine = MainEngine(event_engine)

# 3. Add gateway (Binance)
main_engine.add_gateway(BinanceGateway)

# 4. Connect to exchange
main_engine.connect({
    "API_KEY": BINANCE_API_KEY,
    "API_SECRET": BINANCE_API_SECRET,
    "TESTNET": True
})

# 5. Add CTA strategy engine
cta_engine = main_engine.add_app(CtaStrategyApp)

# 6. Add strategy
cta_engine.add_strategy(
    class_name="MaCrossoverStrategy",
    strategy_name="ma_cross_01",
    vt_symbol="BINANCE:BTCUSDT",
    setting={"fast_ma_length": 10, "slow_ma_length": 30}
)
```

### 7.2 Data Flow

#### Market Data Ingestion
1. Binance WebSocket sends tick/bar data to `BinanceGateway`
2. Gateway converts to VnPy `TickData`/`BarData` objects
3. Events published to `EventEngine`
4. Subscribed components receive events:
   - **Strategies**: `on_tick()` / `on_bar()` callbacks
   - **Risk Manager**: Real-time position tracking
   - **Telegram Bot**: Price updates for dashboard
5. Data cached in Redis and persisted to PostgreSQL

#### Strategy Execution
1. User uploads strategy to `strategies/` directory
2. CTA engine loads strategy on startup
3. Strategy receives market data via `on_bar()` or `on_tick()`
4. Strategy generates signals → calls `buy()`/`sell()`
5. Risk manager validates order (position limits, drawdown)
6. If approved, order sent to gateway → exchange
7. Execution callback updates positions and sends Telegram alert

#### Risk Monitoring
- Each order checked against risk limits
- Portfolio exposure calculated in real-time
- Drawdown protection: auto-stop trading if threshold breached
- Trust scoring system monitors system health

---

## 8. API Reference

### Authentication
All endpoints (except `/health`) require a bearer token:
```
Authorization: Bearer <your_token>
```

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (no auth) |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/webhook` | Telegram updates (no auth) |
| `GET` | `/api/v1/status` | System status |
| `GET` | `/api/v1/positions` | Open positions |
| `GET` | `/api/v1/account` | Account balance |
| `GET` | `/api/v1/trades` | Recent trades |
| `POST` | `/api/v1/strategy/start` | Start a strategy |
| `POST` | `/api/v1/strategy/stop` | Stop a strategy |
| `POST` | `/api/v1/risk/threshold` | Update risk limits |

#### Example: Get Positions
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/positions
```

Response:
```json
{
  "positions": [
    {
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "volume": 0.001,
      "price": 45000.0,
      "pnl": 150.25
    }
  ]
}
```

---

## 9. Running & Managing

### Start/Stop Services

```bash
# Start all services
docker-compose up -d

# View logs (all services)
docker-compose logs -f

# View specific service logs
docker-compose logs -f trading-orchestrator

# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

### Check Service Health

```bash
# Check all services
docker-compose ps

# Test API
curl http://localhost:8000/health

# Check database connection
docker-compose exec postgres psql -U postgres -d vnpy -c "\dt"

# Check Redis
docker-compose exec redis redis-cli ping

# View Prometheus targets
curl http://localhost:9090/api/v1/targets
```

### Hot-Reload Strategies

The `strategies/` directory is mounted as a volume. When you add/modify a Python strategy file:

```bash
# Copy your strategy to the mounted directory
cp my_strategy.py strategies/

# Restart the orchestrator to load it
docker-compose restart trading-orchestrator
```

---

## 10. Monitoring & Observability

### Prometheus Metrics

The orchestrator exposes metrics at `/metrics`:

```promql
# Trading metrics
trading_active_positions
trading_unrealized_pnl_dollars
trading_total_pnl_dollars
trading_trades_total

# Security metrics
security_trust_score
security_audit_events_total

# System metrics
process_cpu_seconds_total
process_resident_memory_bytes
```

### Grafana Dashboards

Pre-configured dashboards available at `http://localhost:3000` (admin/admin):

1. **Trading Overview**
   - Portfolio value over time
   - P&L heatmap
   - Position exposure breakdown

2. **Risk Dashboard**
   - Real-time drawdown
   - Position concentration
   - VaR calculations

3. **Security Monitor**
   - Trust scores by service
   - Authentication attempts
   - Audit event timeline

4. **System Health**
   - Service status
   - API latency
   - Resource utilization

---

## 11. Security Framework

### Four Pillars

1. **mTLS Manager**: Mutual TLS for service-to-service encryption
2. **Secrets Manager**: Vault integration + environment fallback
3. **Audit Logger**: Immutable, hash-chained event logs
4. **Trust Scorer**: Dynamic trust scoring based on behavior

### Trust Scoring Events

| Event | Score Change |
|-------|--------------|
| `AUTH_SUCCESS` | +2.0 |
| `TRADE_EXECUTED` | +0.5 |
| `CONFIG_CHANGE` | -2.0 |
| `ACCESS_VIOLATION` | -20.0 |
| `ANOMALY_DETECTED` | -15.0 |
| `COMPLIANCE_VIOLATION` | -25.0 |

Trust scores below 50 trigger automatic warnings; below 20 trigger system lockdown.

---

## 12. Risk Management

### Risk Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_POSITION_SIZE` | 10% of capital | Max single position |
| `MAX_DAILY_LOSS` | 3% | Daily loss limit |
| `MAX_DRAWDOWN` | 10% | Max drawdown before stop |
| `MAX_LEVERAGE` | 75x | Maximum leverage allowed |
| `MIN_CONFIDENCE` | 65% | Minimum signal confidence |

### Risk Checks (Per-Trade)

1. Position limit check
2. Daily loss check
3. Drawdown check
4. Leverage check
5. Concentration check

If any check fails, order is rejected and risk alert is sent via Telegram.

---

## 13. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **Telegram not sending messages** | Invalid token/chat_id | Verify `.env` values; restart bot |
| **Cannot connect to exchange** | API key/secret wrong | Check Binance credentials in `.env` |
| **Database connection refused** | PostgreSQL not ready | Wait 30s after `docker-compose up`; check logs |
| **Container keeps restarting** | Health check failing | `docker-compose logs <service>` for details |
| **High memory usage** | Redis cache full | Increase Redis `maxmemory` in `docker-compose.yml` |
| **Strategies not loading** | VnPy not installed | Verify `vnpy==4.3.0` in `requirements.txt` |

### Log Locations

- Orchestrator logs: `docker-compose logs trading-orchestrator`
- PostgreSQL logs: `docker-compose logs postgres`
- Redis logs: `docker-compose logs redis`
- Application logs (if mounted): `./logs/`

### Debug Mode

Enable debug logging in `.env`:
```dotenv
LOG_LEVEL=DEBUG
```

Then restart:
```bash
docker-compose restart trading-orchestrator
```

---

## 14. Contributing

We welcome contributions from the community!

### Development Workflow

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/godmode-quant-orchestrator.git
cd godmode-quant-orchestrator

# 2. Create feature branch
git checkout -b feature/your-feature

# 3. Make changes and test
python -m pytest tests/
docker-compose up -d  # If integration testing needed

# 4. Commit with conventional commit
git commit -m "feat: add new RSI strategy"

# 5. Push and open PR
git push origin feature/your-feature
```

### Coding Standards

- **Python**: PEP 8, type hints required
- **Testing**: All new code must have unit tests (≥80% coverage)
- **Docstrings**: Google style for functions/classes
- **Imports**: Sort with `isort`; lint with `ruff`
- **Docker**: Keep images small; use multi-stage builds

### Adding New Strategies

1. Create file in `strategies/` directory
2. Extend `CtaTemplate`
3. Implement required methods: `on_init`, `on_start`, `on_stop`, `on_bar`
4. Add to `__init__.py` registration
5. Test with paper trading first!

### Adding New Gateways

1. Create new gateway class extending `BaseGateway`
2. Implement required methods: `connect`, `subscribe`, `send_order`, `cancel_order`
3. Register with `main_engine.add_gateway()`
4. Add to `requirements.txt` if new dependencies

---

## 15. License & Support

### License

MIT License - see [LICENSE](LICENSE) file for details.

### Support

- 📖 **Documentation**: This repository's `/docs` folder
- 🐛 **Issues**: [GitHub Issues](https://github.com/NkhekheRepository/godmode-quant-orchestrator/issues)
- 💬 **Telegram Bot**: @NkhekheQuantBot (for live trading alerts)
- 📧 **Email**: support@example.com

### Disclaimer

⚠️ **Important**: Cryptocurrency and futures trading involves substantial risk. This software is provided for educational purposes. Always paper trade extensively before using real capital. Never invest more than you can afford to lose. Past performance does not guarantee future results.

---

## Quick Reference

### Port Mapping
| Service | External | Internal |
|---------|----------|----------|
| Orchestrator API | 8000 | 8000 |
| PostgreSQL | 5433 | 5432 |
| Redis | 6380 | 6379 |
| Prometheus | 9090 | 9090 |
| Grafana | 3000 | 3000 |
| ML Forecast | 8001 | 8000 |
| ML Sentiment | 8002 | 8000 |

### Useful Commands
```bash
# Restart everything
docker-compose restart

# Rebuild after code changes
docker-compose build --no-cache

# View all logs
docker-compose logs -f --tail=100

# Executive into container
docker-compose exec trading-orchestrator bash

# Backup database
docker-compose exec postgres pg_dump -U postgres vnpy > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres vnpy < backup.sql
```

---

**Happy Trading! 📈✨**

*Built with ❤️ on VnPy, Docker, and lots of coffee ☕*