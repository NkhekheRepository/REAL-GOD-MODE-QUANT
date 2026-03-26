# God Mode Quant Trading Orchestrator

> A production-ready quant trading orchestrator built with VNPy (v3.9.4) backbone, featuring Telegram dashboard, risk management, security framework (mTLS, secrets, audit, trust scoring), and comprehensive monitoring.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![VNPy Version](https://img.shields.io/badge/vnpy-3.9.4-brightgreen.svg)](https://www.vnpy.com/)
[![Docker](https://img.shields.io/badge/docker-%E2%86%92-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Features](#features)
  - [Trading Engine](#trading-engine)
  - [Telegram Dashboard](#telegram-dashboard)
  - [Security Framework](#security-framework)
  - [Monitoring](#monitoring)
  - [AI/ML Services](#aiml-services)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The God Mode Quant Trading Orchestrator is a comprehensive quantitative trading system designed to orchestrate algorithmic trading strategies with production-grade security, monitoring, and control capabilities.

### Key Capabilities

- **VNPy 3.9.4 Backbone**: Industry-leading open-source quantitative trading framework
- **Telegram Dashboard**: Real-time trading monitoring via Telegram bot with inline keyboards
- **Security Framework**: mTLS, secrets management, audit logging, and trust scoring
- **Risk Management**: Position limits, drawdown protection, portfolio risk monitoring
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **AI/ML Services**: Time series forecasting and sentiment analysis

## Quick Start

Get running in 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/godmode-quant-orchestrator.git
cd godmode-quant-orchestrator

# 2. Configure environment
cp .env.example .env
# Edit .env with your Telegram bot token and chat ID

# 3. Start with Docker Compose
docker-compose up -d

# 4. Check status
docker-compose logs -f trading-orchestrator
```

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GOD MODE QUANT ORCHESTRATOR                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐  │
│  │   Telegram       │   │   Trading        │   │   Security           │  │
│  │   Dashboard      │◄──►│   Engine (VNPy)  │◄──►│   Framework          │  │
│  │   (Bot + UI)     │   │                  │   │                      │  │
│  └──────────────────┘   └──────────────────┘   └──────────────────────┘  │
│          │                       │                       │                  │
│          │                       │                       │                  │
│  ┌───────┴───────────────────────┴───────────────────────┴──────────────┐  │
│  │                         FLASK API LAYER                               │  │
│  │  /health  /metrics  /webhook                                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
├────────────────────────────────────┼────────────────────────────────────────┤
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      INFRASTRUCTURE LAYER                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ PostgreSQL  │  │    Redis    │  │ Prometheus │  │  Grafana    │  │  │
│  │  │  (Port 5433)│  │  (Port 6380)│  │ (Port 9090)│  │  (Port 3000)│  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      ML SERVICES LAYER                                │  │
│  │  ┌────────────────────────┐    ┌────────────────────────┐            │  │
│  │  │ Time Series Forecast  │    │  Sentiment Analysis    │            │  │
│  │  │ (Random Forest)        │    │  (NLP)                 │            │  │
│  │  └────────────────────────┘    └────────────────────────┘            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture.

## Features

### Trading Engine

Built on VNPy 3.9.4, supporting:

- **CTA Strategy Engine**: Backtesting and live trading
- **Multiple Strategies**: MA Crossover and extensible framework
- **Order Management**: Local and exchange orders
- **Risk Controls**: Position limits, drawdown protection

```python
# Adding a strategy
cta_engine.add_strategy(
    class_name="MaCrossoverStrategy",
    strategy_name="ma_crossover_01",
    vt_symbol="BINANCE:BTCUSDT",
    setting={"fast_ma_length": 10, "slow_ma_length": 30}
)
```

### Telegram Dashboard

Comprehensive Telegram bot with:

- **Real-time Notifications**: Trade entries, exits, P&L updates
- **Risk Alerts**: Drawdown warnings, position limit breaches
- **Trust Score Monitoring**: Security posture notifications
- **Interactive Commands**: `/status`, `/positions`, `/risk`, `/trust`, `/pnl`, `/summary`
- **Inline Keyboards**: Quick action buttons

```
┌─────────────────────────────────────┐
│  🤖 GOD MODE QUANT BOT              │
├─────────────────────────────────────┤
│  📈 Status    │ 📊 Positions        │
│  🛡️ Risk     │ 🎯 Trust            │
│  💰 P&L      │ 📋 Summary          │
│  🔔 Alerts On │ ⛔️ Alerts Off       │
└─────────────────────────────────────┘
```

See [TELEGRAM_DASHBOARD.md](TELEGRAM_DASHBOARD.md) for complete documentation.

### Security Framework

Four pillars of security:

1. **mTLS Manager**: Mutual TLS for service-to-service communication
2. **Secrets Manager**: HashiCorp Vault integration + environment fallback
3. **Audit Logger**: Immutable, tamper-evident event logging
4. **Trust Scorer**: Dynamic trust scoring based on behavior analysis

```python
# Trust scoring example
from security.trust_scorer import record_trust_event, TrustEventType

record_trust_event(
    service_or_user="orchestrator:system",
    event_type=TrustEventType.AUTH_SUCCESS,
    service="orchestrator",
    user="system",
    description="System startup"
)
```

### Monitoring

Full-stack monitoring with Prometheus and Grafana:

- **Trading Metrics**: Positions, P&L, trade execution
- **Security Metrics**: Trust scores, authentication events
- **System Metrics**: Health checks, latency
- **Dashboards**: Pre-configured Grafana dashboards

| Service    | Port | URL                  |
|------------|------|----------------------|
| Orchestrator | 8000 | http://localhost:8000 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana    | 3000 | http://localhost:3000 |

### AI/ML Services

- **Time Series Forecast**: Random Forest-based price prediction
- **Sentiment Analysis**: NLP-based market sentiment from news/social

## Installation

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.9+ (for local development)

### Docker Deployment (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run the orchestrator
python main.py
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | Yes | - |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | Yes | - |
| `POSTGRES_USER` | PostgreSQL username | No | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | No | `postgres` |
| `POSTGRES_DB` | Database name | No | `vnpy` |
| `REDIS_PASSWORD` | Redis password | No | (none) |
| `GRAFANA_PASSWORD` | Grafana admin password | No | `admin` |

### Telegram Setup

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your bot token
3. Start a chat with your bot
4. Get your chat ID from [@userinfobot](https://t.me/userinfobot)

## Usage

### Running the System

```bash
# Start all services
docker-compose up -d

# Check service health
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics
```

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/status` | Portfolio and system status |
| `/positions` | Open positions |
| `/risk` | Risk report |
| `/trust` | Trust score |
| `/pnl` | P&L summary |
| `/summary` | Daily summary |
| `/alerts` | Alert settings |
| `/help` | Help message |

## API Reference

### Health Check

```bash
GET /health
```

Response:
```json
{"status": "healthy", "service": "god-mode-quant-orchestrator"}
```

### Prometheus Metrics

```bash
GET /metrics
```

Returns Prometheus-format metrics.

### Telegram Webhook

```bash
POST /webhook
```

Receives Telegram bot updates.

See [API.md](API.md) for complete API documentation.

## Troubleshooting

### Common Issues

1. **Telegram notifications not working**
   - Verify bot token and chat ID
   - Ensure bot is started in the chat

2. **Database connection failures**
   - Check PostgreSQL container health
   - Verify credentials in .env

3. **Strategy not loading**
   - Check VNPy installation
   - Verify strategy settings

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

```bash
# Fork and clone
git clone https://github.com/yourusername/godmode-quant-orchestrator.git

# Create feature branch
git checkout -b feature/your-feature

# Make changes and test
python -m pytest

# Commit and push
git commit -m "feat: Add new feature"
git push origin feature/your-feature

# Open PR
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Last Updated**: March 26, 2026  
**Version**: 1.0.0

*Happy trading! 📈*
