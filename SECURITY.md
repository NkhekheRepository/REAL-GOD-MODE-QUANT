# Security Framework Guide

> Comprehensive guide to the God Mode Quant Trading Orchestrator security framework

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Usage](#usage)
- [Configuration](#configuration)

## Overview

The God Mode Quant Trading Orchestrator includes a comprehensive four-pillar security framework:

1. **mTLS Manager**: Mutual TLS for service-to-service communication
2. **Secrets Manager**: HashiCorp Vault integration with environment fallback
3. **Audit Logger**: Immutable, tamper-evident event logging
4. **Trust Scorer**: Dynamic trust scoring based on behavior analysis

## Components

### 1. mTLS Manager (`security/mtls_manager.py`)

Provides mutual TLS certificate management for secure service communication.

**Features:**
- SSL context creation with client certificate validation
- Peer certificate validation
- Certificate rotation support
- Caching for performance

**Key Classes:**
```python
from security.mtls_manager import MTLSManager, mtls_manager

# Create SSL context for a service
context = mtls_manager.create_ssl_context(
    service_name="binance",
    require_client_cert=True
)

# Validate peer certificate
is_valid = mtls_manager.validate_peer_certificate(cert)

# Trigger certificate rotation
mtls_manager.rotate_certificates("binance")
```

### 2. Secrets Manager (`security/secrets_manager.py`)

Manages secrets from HashiCorp Vault or environment variables with caching.

**Features:**
- HashiCorp Vault integration
- Environment variable fallback
- 5-minute TTL caching
- Automatic secret rotation

**Convenience Functions:**
```python
from security.secrets_manager import (
    get_binance_api_key,
    get_binance_api_secret,
    get_telegram_bot_token,
    get_telegram_chat_id
)

# Get API keys (automatically checks Vault, then env vars)
api_key = get_binance_api_key()
api_secret = get_binance_api_secret()
```

### 3. Audit Logger (`security/audit_logger.py`)

Provides immutable audit logging with hash chain verification.

**Features:**
- SHA-256 hash chaining for tamper evidence
- Log integrity verification
- Event categorization (SECURITY, TRADE, AUTH, CONFIG)
- JSON format for easy parsing

**Usage:**
```python
from security.audit_logger import (
    log_security_event,
    log_trade_event,
    log_auth_event,
    log_config_event
)

# Log security events
log_security_event(
    service="orchestrator",
    user="system",
    action="startup",
    outcome="success",
    details={"version": "1.0.0"}
)

# Log trade events
log_trade_event(
    service="orchestrator",
    user="strategy",
    action="order_submitted",
    outcome="success",
    details={"symbol": "BTCUSDT", "side": "BUY"}
)

# Log authentication events
log_auth_event(
    service="api",
    user="trader1",
    action="login",
    outcome="success"
)

# Verify log integrity
from security.audit_logger import audit_logger
is_valid = audit_logger.verify_log_integrity()
```

**Audit Log Entry Format:**
```json
{
  "timestamp": "2026-03-26T12:00:00Z",
  "event_type": "SECURITY",
  "service": "orchestrator",
  "user": "system",
  "action": "startup",
  "outcome": "success",
  "severity": "INFO",
  "details": {"version": "1.0.0"},
  "previous_hash": "abc123...",
  "hash": "def456..."
}
```

### 4. Trust Scorer (`security/trust_scorer.py`)

Dynamic trust scoring system that monitors service behavior.

**Features:**
- Event-based trust scoring (0-100 scale)
- Time-based decay (1% daily)
- Configurable event weights
- Detailed trust reports

**Event Types and Weights:**

| Event Type | Weight | Description |
|------------|--------|-------------|
| AUTH_SUCCESS | +2.0 | Successful authentication |
| AUTH_FAILURE | -10.0 | Failed authentication |
| TRADE_EXECUTED | +0.5 | Trade executed |
| TRADE_FAILED | -5.0 | Trade failure |
| CONFIG_CHANGE | -2.0 | Configuration change |
| ACCESS_VIOLATION | -20.0 | Access violation |
| CERTIFICATE_ROTATED | +5.0 | Certificate rotation |
| SECRET_ACCESSED | +0.1 | Secret accessed |
| ANOMALY_DETECTED | -15.0 | Anomaly detected |
| COMPLIANCE_VIOLATION | -25.0 | Compliance violation |

**Usage:**
```python
from security.trust_scorer import (
    TrustScorer,
    TrustEventType,
    trust_scorer,
    record_trust_event,
    get_trust_score,
    get_trust_report
)

# Record events
record_trust_event(
    service_or_user="orchestrator:system",
    event_type=TrustEventType.AUTH_SUCCESS,
    service="orchestrator",
    user="system",
    description="System startup"
)

# Get current trust score
score = get_trust_score("orchestrator:system")
print(f"Trust score: {score:.1f}/100")

# Get detailed report
report = get_trust_report("orchestrator:system")
print(f"Trustworthy: {report.get('is_trustworthy')}")
print(f"Needs attention: {report.get('needs_attention')}")

# Predefined event recorders
from security.trust_scorer import (
    record_auth_success,
    record_auth_failure,
    record_trade_executed,
    record_access_violation,
    record_certificate_rotated
)

record_auth_success("api", "trader1")
record_trade_executed("strategy", "system", "BTCUSDT")
```

**Trust Score Thresholds:**
- **> 70**: Trustworthy (green)
- **50-70**: Medium (yellow)
- **< 50**: Needs attention (red)

## Configuration

### Environment Variables

```bash
# Vault configuration (optional)
VAULT_ADDR=https://vault.example.com:8200
VAULT_TOKEN=your_vault_token

# Certificate directory
VNPY_CERT_DIR=/path/to/certs

# Audit log directory
VNPY_AUDIT_LOG_DIR=/var/log/audit
```

### Custom Event Weights

```python
from security.trust_scorer import TrustScorer

scorer = TrustScorer()
scorer.event_weights = {
    TrustEventType.AUTH_SUCCESS: 3.0,
    TrustEventType.AUTH_FAILURE: -15.0,
    # ... custom weights
}
```

---

**Related Documentation:**
- [README.md](README.md) - Main project documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
