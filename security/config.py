"""
Security Configuration Module
Provides centralized security settings for the GodMode Quant Orchestrator
"""
import os
from typing import Dict, List

# Rate Limiting Configuration
RATE_LIMITS = {
    "default": ["200 per day", "50 per hour"],
    "health_check": "100 per minute",
    "metrics": "50 per minute",
    "api_endpoints": "10 per minute"
}

# Authentication Configuration
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"
API_USERNAME = os.getenv("API_USERNAME", "admin")
API_PASSWORD = os.getenv("API_PASSWORD", "admin")

# Security Headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
}

# CORS Configuration
ALLOWED_ORIGINS = [
    os.getenv("CORS_ORIGIN", "http://localhost:3000"),
    "https://dashboard.godmode-quant.com"
]

# WebSocket Configuration
WS_ALLOWED_ORIGINS = ALLOWED_ORIGINS
WS_MAX_CONNECTIONS = 100

# SSL/TLS Configuration
SSL_VERIFY_ENABLED = os.getenv("SSL_VERIFY", "true").lower() == "true"
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", "")

# Session Configuration
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())

# JWT Configuration (if using JWT instead of Basic Auth)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Logging Configuration
LOG_SECURITY_EVENTS = os.getenv("LOG_SECURITY_EVENTS", "true").lower() == "true"
SECURITY_LOG_LEVEL = os.getenv("SECURITY_LOG_LEVEL", "INFO")

# Input Validation
MAX_SYMBOL_LENGTH = 10
MAX_MESSAGE_LENGTH = 4096
ALLOWED_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
    "SOLUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "AVAXUSDT"
]
ALLOWED_ORDER_TYPES = ["MARKET", "LIMIT", "STOP", "TAKE_PROFIT"]
ALLOWED_POSITION_SIDES = ["LONG", "SHORT", "BOTH"]


def get_security_headers() -> Dict[str, str]:
    """Get security headers for responses"""
    return SECURITY_HEADERS


def is_origin_allowed(origin: str) -> bool:
    """Check if origin is allowed for CORS/WebSocket"""
    return origin in ALLOWED_ORIGINS if origin else False


def is_symbol_valid(symbol: str) -> bool:
    """Validate trading symbol"""
    if not symbol or len(symbol) > MAX_SYMBOL_LENGTH:
        return False
    if symbol.upper() not in ALLOWED_SYMBOLS:
        return False
    return True


def is_order_type_valid(order_type: str) -> bool:
    """Validate order type"""
    return order_type.upper() in ALLOWED_ORDER_TYPES


def is_position_side_valid(side: str) -> bool:
    """Validate position side"""
    return side.upper() in ALLOWED_POSITION_SIDES


def sanitize_input(value: str, max_length: int = None) -> str:
    """Sanitize user input"""
    if not value:
        return ""
    
    # Truncate to max length
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    # Remove potentially dangerous characters
    dangerous_chars = [";", "--", "/*", "*/", "<", ">"]
    for char in dangerous_chars:
        value = value.replace(char, "")
    
    # Strip whitespace
    value = value.strip()
    
    return value


def log_security_event(event_type: str, details: Dict, severity: str = "INFO"):
    """Log security event"""
    if not LOG_SECURITY_EVENTS:
        return
    
    import logging
    from datetime import datetime
    
    security_logger = logging.getLogger("security")
    
    security_logger.log(
        getattr(logging, severity.upper()),
        f"[{datetime.utcnow().isoformat()}] "
        f"EVENT={event_type} "
        f"SEVERITY={severity} "
        f"DETAILS={details}"
    )