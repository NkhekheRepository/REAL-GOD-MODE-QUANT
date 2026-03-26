# Quickstart Guide

> Get the God Mode Quant Trading Orchestrator running in 5 minutes

## Prerequisites

Before you begin, ensure you have:

- [ ] **Docker Engine** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- [ ] **Docker Compose** 2.0+ (included with Docker Desktop)
- [ ] **Git** ([Install Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git))

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/godmode-quant-orchestrator.git
cd godmode-quant-orchestrator
```

## Step 2: Configure Telegram

You need a Telegram bot for notifications:

1. **Create a bot**:
   - Open Telegram and search for **@BotFather**
   - Send `/newbot`
   - Follow the prompts to name your bot
   - Copy the bot token

2. **Get your chat ID**:
   - Search for **@userinfobot**
   - Send `/start`
   - Copy your chat ID

3. **Configure the environment**:
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Edit with your Telegram credentials
   nano .env
   ```

   Update these values:
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

## Step 3: Start the System

```bash
# Start all services in detached mode
docker-compose up -d
```

Expected output:
```
[+] Running 8/8
 ✔ Container godmode-quant-orchestrator-ml-sentiment-analysis-1  Healthy
 ✔ Container godmode-quant-orchestrator-postgres-1                  Healthy
 ✔ Container godmode-quant-orchestrator-redis-1                     Healthy
 ✔ Container godmode-quant-orchestrator-ml-time-series-forecast-1    Healthy
 ✔ Container godmode-quant-orchestrator-grafana-1                   Healthy
 ✔ Container godmode-quant-orchestrator-prometheus-1                Healthy
 ✔ Container godmode-quant-orchestrator-trading-orchestrator-1     Started
```

## Step 4: Verify Installation

### Check Service Health

```bash
# Check orchestrator health
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "god-mode-quant-orchestrator"}
```

### Check Logs

```bash
# View orchestrator logs
docker-compose logs -f trading-orchestrator
```

You should see:
```
=== GOD MODE QUANT TRADING ORCHESTRATOR STARTING ===
VNPY imported successfully: 3.9.4
Enhanced Telegram Dashboard initialized successfully
Prometheus metrics server started on port 9090
Telegram notification sent successfully
Trading orchestrator started. Entering main loop...
```

### Check Telegram

You should receive a startup message in your Telegram chat:
```
🤖 GOD MODE QUANT ORCHESTRATOR

Trading system is now ONLINE

Monitoring and alerts active
Use /help for available commands

🔔 Waiting for trades...
```

## Step 5: Explore the Dashboard

### Access Services

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Orchestrator API | http://localhost:8000 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |

### Telegram Commands

Try these commands in your Telegram chat:

```
/status      # Check portfolio status
/positions   # View open positions
/risk        # View risk report
/trust       # Check trust score
/pnl         # View P&L
/help        # Get help
```

### Inline Keyboards

Click the buttons below messages for quick actions:
- 📈 Status - System status
- 📊 Positions - Open positions
- 🛡️ Risk - Risk report
- 🎯 Trust - Trust score
- 💰 P&L - P&L summary

## What's Next?

### 1. Configure Trading Strategies

Edit strategies in `strategies/ma_crossover_strategy.py` or add new strategies.

### 2. Set Up Grafana Dashboards

1. Open http://localhost:3000
2. Login with admin/admin
3. Import dashboards from `monitoring/`

### 3. Configure Risk Limits

Edit risk thresholds in code or environment:
```python
alert_thresholds = {
    "max_drawdown": 10.0,        # 10%
    "max_position_risk": 2.0,   # 2% per position
    "max_portfolio_risk": 5.0,  # 5% total
}
```

### 4. Add Exchange Connections

Configure exchange API keys in `.env`:
```bash
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

## Common Operations

### Stop the System

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

### View All Logs

```bash
docker-compose logs -f
```

### Update and Rebuild

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Reset Everything (including data)

```bash
docker-compose down -v
docker-compose up -d
```

## Troubleshooting

### Telegram Not Working

1. Check bot token is correct
2. Start a chat with your bot
3. Verify chat ID
4. Check logs: `docker-compose logs trading-orchestrator`

### Database Connection Issues

```bash
# Check PostgreSQL
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres
```

### Port Conflicts

If ports are already in use, edit `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Change external port
```

## Quick Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics
```

---

**Need more details?**
- [README.md](README.md) - Full documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [API.md](API.md) - API reference
- [TELEGRAM_DASHBOARD.md](TELEGRAM_DASHBOARD.md) - Telegram bot guide
