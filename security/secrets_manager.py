"""
Secrets Manager for vnpy-based God Mode Quant Trading Orchestrator
Handles secure retrieval and caching of secrets from HashiCorp Vault or similar
"""
import os
import logging
import threading
from typing import Dict, Optional, Any
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages secrets retrieval from Vault or environment variables"""
    
    def __init__(self, vault_addr: str = None, vault_token: str = None):
        """
        Initialize secrets manager
        
        Args:
            vault_addr: Vault server address (optional, can use VAULT_ADDR env var)
            vault_token: Vault token (optional, can use VAULT_TOKEN env var)
        """
        self.vault_addr = vault_addr or os.getenv('VAULT_ADDR')
        self.vault_token = vault_token or os.getenv('VAULT_TOKEN')
        self._secrets_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl: Dict[str, float] = {}  # timestamp when cache expires
        self.default_ttl = 300  # 5 minutes default TTL
        
        # Try to import hvac (Vault client)
        self._hvac_available = False
        try:
            import hvac
            self._hvac_available = True
            logger.info("HVAC (Vault client) available")
        except ImportError:
            logger.warning("HVAC not available, falling back to environment variables")
    
    def get_secret(self, path: str, key: str = None, use_cache: bool = True) -> Any:
        """
        Retrieve a secret from Vault or environment variables
        
        Args:
            path: Secret path in Vault (e.g., 'secret/data/binance/api')
            key: Specific key within the secret (if None, returns entire secret)
            use_cache: Whether to use cached values
            
        Returns:
            Secret value or None if not found
        """
        cache_key = f"{path}:{key}" if key else path
        
        # Check cache first
        if use_cache and self._is_cached_valid(cache_key):
            with self._cache_lock:
                return self._secrets_cache.get(cache_key)
        
        # Retrieve secret
        secret_value = self._fetch_secret(path, key)
        
        # Cache the result
        if secret_value is not None and use_cache:
            with self._cache_lock:
                self._secrets_cache[cache_key] = secret_value
                self._cache_ttl[cache_key] = time.time() + self.default_ttl
        
        return secret_value
    
    def _is_cached_valid(self, cache_key: str) -> bool:
        """Check if cached value is still valid"""
        with self._cache_lock:
            if cache_key not in self._secrets_cache:
                return False
            if cache_key not in self._cache_ttl:
                return False
            return time.time() < self._cache_ttl[cache_key]
    
    def _fetch_secret(self, path: str, key: str = None) -> Any:
        """Fetch secret from Vault or environment variables"""
        # Try Vault first if available and configured
        if self._hvac_available and self.vault_addr and self.vault_token:
            try:
                return self._fetch_from_vault(path, key)
            except Exception as e:
                logger.warning(f"Failed to fetch secret from Vault: {e}. Falling back to environment variables.")
        
        # Fallback to environment variables
        return self._fetch_from_env(path, key)
    
    def _fetch_from_vault(self, path: str, key: str = None) -> Any:
        """Fetch secret from HashiCorp Vault"""
        import hvac
        
        client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        
        if not client.is_authenticated():
            raise Exception("Vault client not authenticated")
        
        # Read secret from Vault
        # Note: This assumes KV v2 engine at 'secret/'
        # Adjust path as needed for your Vault setup
        secret_path = f"secret/data/{path}" if not path.startswith('secret/') else path
        
        response = client.secrets.kv.v2.read_secret_version(path=secret_path.replace('secret/data/', ''))
        
        if key:
            return response['data']['data'].get(key)
        else:
            return response['data']['data']
    
    def _fetch_from_env(self, path: str, key: str = None) -> Any:
        """Fetch secret from environment variables"""
        # Convert path to environment variable format
        # e.g., 'binance/api_key' -> 'BINANCE_API_KEY'
        env_key = path.upper().replace('/', '_').replace('-', '_')
        
        if key:
            # For nested keys, try PATH_KEY format
            env_key = f"{env_key}_{key.upper()}"
        
        value = os.getenv(env_key)
        
        if value is None:
            logger.debug(f"Environment variable {env_key} not found")
            return None
            
        # Try to parse as JSON if it looks like JSON
        if value.startswith('{') and value.endswith('}'):
            try:
                import json
                parsed = json.loads(value)
                return parsed.get(key) if key else parsed
            except json.JSONDecodeError:
                pass  # Return as string if not valid JSON
        
        return value
    
    def rotate_secret(self, path: str, key: str = None) -> bool:
        """
        Mark a secret for rotation (clear cache)
        
        Args:
            path: Secret path in Vault
            key: Specific key within the secret
            
        Returns:
            True if cache was cleared
        """
        cache_key = f"{path}:{key}" if key else path
        
        with self._cache_lock:
            if cache_key in self._secrets_cache:
                del self._secrets_cache[cache_key]
            if cache_key in self._cache_ttl:
                del self._cache_ttl[cache_key]
            
        logger.info(f"Secret cache cleared for {cache_key}")
        return True
    
    def is_vault_configured(self) -> bool:
        """Check if Vault is properly configured"""
        return bool(self._hvac_available and self.vault_addr and self.vault_token)


# Global secrets manager instance
secrets_manager = SecretsManager()


# Convenience functions
def get_secret(path: str, key: str = None) -> Any:
    """Get a secret using the global secrets manager"""
    return secrets_manager.get_secret(path, key)


def get_binance_api_key() -> str:
    """Get Binance API key"""
    return get_secret('binance/api', 'api_key') or os.getenv('BINANCE_API_KEY', '')


def get_binance_api_secret() -> str:
    """Get Binance API secret"""
    return get_secret('binance/api', 'api_secret') or os.getenv('BINANCE_API_SECRET', '')


def get_coinbase_api_key() -> str:
    """Get Coinbase API key"""
    return get_secret('coinbase/api', 'api_key') or os.getenv('COINBASE_API_KEY', '')


def get_coinbase_api_secret() -> str:
    """Get Coinbase API secret"""
    return get_secret('coinbase/api', 'api_secret') or os.getenv('COINBASE_API_SECRET', '')


def get_telegram_bot_token() -> str:
    """Get Telegram bot token"""
    return get_secret('telegram/bot', 'token') or os.getenv('TELEGRAM_BOT_TOKEN', '')


def get_telegram_chat_id() -> str:
    """Get Telegram chat ID"""
    return get_secret('telegram/chat', 'id') or os.getenv('TELEGRAM_CHAT_ID', '')