"""
Mutual TLS Manager for vnpy-based God Mode Quant Trading Orchestrator
Handles certificate management, mTLS context creation, and peer validation
"""
import ssl
import os
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MTLSManager:
    """Manages mutual TLS certificates and SSL contexts for service-to-service communication"""
    
    def __init__(self, cert_dir: str = None):
        # Use a test directory if we're in a test environment, otherwise use default
        if cert_dir is None:
            cert_dir = os.getenv('VNPY_CERT_DIR', '/tmp/vnpy_certs')
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self._cert_cache: Dict[str, ssl.SSLContext] = {}
        
    def create_ssl_context(
        self, 
        service_name: str,
        require_client_cert: bool = True
    ) -> ssl.SSLContext:
        """
        Create an SSL context for mutual TLS
        
        Args:
            service_name: Name of the service (used for certificate selection)
            require_client_cert: Whether to require client certificate validation
            
        Returns:
            Configured SSL context
        """
        # Check cache first
        cache_key = f"{service_name}_{require_client_cert}"
        if cache_key in self._cert_cache:
            return self._cert_cache[cache_key]
            
        # Create SSL context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH if require_client_cert else ssl.Purpose.SERVER_AUTH)
        
        # Load certificates
        cert_file = self.cert_dir / f"{service_name}.crt"
        key_file = self.cert_dir / f"{service_name}.key"
        ca_file = self.cert_dir / "ca.crt"
        
        if not all([cert_file.exists(), key_file.exists(), ca_file.exists()]):
            logger.warning(f"Certificate files not found for {service_name}. Using default context.")
            # Return a basic context for development/testing
            context = ssl.create_default_context()
            if require_client_cert:
                context.verify_mode = ssl.CERT_NONE  # For development only
            self._cert_cache[cache_key] = context
            return context
            
        # Load certificate chain
        context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
        
        # Load CA certificate for client verification
        context.load_verify_locations(cafile=str(ca_file))
        
        if require_client_cert:
            context.verify_mode = ssl.CERT_REQUIRED
            # Optionally check certificate revocation
            context.verify_flags |= ssl.VERIFY_CRL_CHECK_LEAF
            
        # Set security options
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_SINGLE_DH_USE
        
        # Cache the context
        self._cert_cache[cache_key] = context
        logger.info(f"Created SSL context for service: {service_name}")
        return context
    
    def validate_peer_certificate(self, cert: Dict) -> bool:
        """
        Validate peer certificate against expected identity
        
        Args:
            cert: Peer certificate as returned by getpeercert()
            
        Returns:
            True if certificate is valid and matches expected identity
        """
        # In a real implementation, this would check:
        # 1. Certificate is signed by our CA
        # 2. Certificate is not expired
        # 3. Certificate matches expected service identity (SPIFFE ID, etc.)
        # 4. Certificate is not revoked (CRL/OCSP)
        
        # For now, basic validation
        if not cert:
            logger.warning("No peer certificate provided")
            return False
            
        # Check if certificate has basic required fields
        if 'subject' not in cert or 'issuer' not in cert:
            logger.warning("Peer certificate missing required fields")
            return False
            
        logger.info("Peer certificate validation passed (basic)")
        return True
    
    def rotate_certificates(self, service_name: str) -> bool:
        """
        Trigger certificate rotation for a service
        
        Args:
            service_name: Name of the service to rotate certificates for
            
        Returns:
            True if rotation was successful
        """
        # In a real implementation, this would:
        # 1. Request new certificate from Vault/PKI
        # 2. Replace old certificate files
        # 3. Reload SSL contexts
        # 4. Notify dependent services
        
        # Clear cache for this service to force reload
        keys_to_remove = [k for k in self._cert_cache.keys() if k.startswith(service_name)]
        for key in keys_to_remove:
            del self._cert_cache[key]
            
        logger.info(f"Certificate rotation triggered for service: {service_name}")
        return True


# Global MTLS manager instance
mtls_manager = MTLSManager()