"""
Audit Logger for vnpy-based God Mode Quant Trading Orchestrator
Provides immutable, tamper-evident logging of all security-relevant events
"""
import json
import logging
import hashlib
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditLogger:
    """Immutable audit logger with chain hashing for tamper evidence"""
    
    def __init__(self, log_dir: str = None):
        # Use a test directory if we're in a test environment, otherwise use default
        if log_dir is None:
            log_dir = os.getenv('VNPY_AUDIT_LOG_DIR', '/tmp/vnpy_audit_logs')
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        self.last_hash = self._get_last_hash()
        
    def _get_last_hash(self) -> str:
        """Get the hash of the last entry in the current log file"""
        if not self.current_log_file.exists():
            return "0" * 64  # Genesis hash
            
        try:
            with open(self.current_log_file, 'r') as f:
                lines = f.readlines()
                if not lines:
                    return "0" * 64
                last_line = lines[-1].strip()
                if last_line:
                    entry = json.loads(last_line)
                    return entry.get("hash", "0" * 64)
        except Exception as e:
            logger.warning(f"Could not read last hash from log file: {e}")
            return "0" * 64
            
    def _compute_entry_hash(self, entry: Dict[str, Any]) -> str:
        """Compute hash for an audit entry"""
        # Create a copy without the hash field
        entry_copy = entry.copy()
        entry_copy.pop("hash", None)
        
        # Sort keys for consistent hashing
        sorted_entry = json.dumps(entry_copy, sort_keys=True)
        
        # Include previous hash for chaining
        chained_input = f"{self.last_hash}{sorted_entry}"
        
        return hashlib.sha256(chained_input.encode()).hexdigest()
    
    def log_event(self, event_type: str, service: str, user: str, 
                  action: str, outcome: str, details: Optional[Dict[str, Any]] = None,
                  severity: str = "INFO") -> bool:
        """
        Log an audit event
        
        Args:
            event_type: Type of event (AUTH, TRADE, CONFIG, etc.)
            service: Service generating the event
            user: User or service account
            action: Action performed
            outcome: Success/failure indicator
            details: Additional event details
            severity: Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            True if logged successfully
        """
        try:
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            entry = {
                "timestamp": timestamp,
                "event_type": event_type,
                "service": service,
                "user": user,
                "action": action,
                "outcome": outcome,
                "severity": severity,
                "details": details or {},
                "previous_hash": self.last_hash
            }
            
            # Compute hash for this entry
            entry["hash"] = self._compute_entry_hash(entry)
            
            # Write to log file
            with open(self.current_log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            
            # Update last hash for chaining
            self.last_hash = entry["hash"]
            
            # Also log to standard logger for immediate visibility
            log_message = f"AUDIT [{event_type}] {service}:{user} {action} -> {outcome}"
            if severity == "ERROR":
                logger.error(log_message)
            elif severity == "WARNING":
                logger.warning(log_message)
            elif severity == "DEBUG":
                logger.debug(log_message)
            else:
                logger.info(log_message)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            return False
    
    def verify_log_integrity(self, log_file_path: Optional[str] = None) -> bool:
        """
        Verify the integrity of the audit log chain
        
        Args:
            log_file_path: Path to log file to verify (uses current if None)
            
        Returns:
            True if log chain is intact
        """
        log_file = Path(log_file_path) if log_file_path else self.current_log_file
        
        if not log_file.exists():
            logger.warning(f"Log file does not exist: {log_file}")
            return True  # Empty file is considered valid
            
        try:
            expected_previous_hash = "0" * 64  # Genesis hash
            
            with open(log_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        entry = json.loads(line)
                        
                        # Check required fields
                        required_fields = ["timestamp", "event_type", "service", "user", 
                                         "action", "outcome", "hash", "previous_hash"]
                        for field in required_fields:
                            if field not in entry:
                                logger.error(f"Missing field '{field}' in audit log line {line_num}")
                                return False
                        
                        # Verify hash chain
                        if entry["previous_hash"] != expected_previous_hash:
                            logger.error(f"Hash chain broken at line {line_num}")
                            logger.error(f"Expected previous hash: {expected_previous_hash}")
                            logger.error(f"Actual previous hash: {entry['previous_hash']}")
                            return False
                        
                        # Verify entry hash
                        computed_hash = self._compute_entry_hash(entry)
                        if entry["hash"] != computed_hash:
                            logger.error(f"Entry hash mismatch at line {line_num}")
                            logger.error(f"Expected hash: {computed_hash}")
                            logger.error(f"Actual hash: {entry['hash']}")
                            return False
                        
                        # Update expected hash for next iteration
                        expected_previous_hash = entry["hash"]
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in audit log line {line_num}: {e}")
                        return False
                    except Exception as e:
                        logger.error(f"Error processing audit log line {line_num}: {e}")
                        return False
            
            logger.info(f"Audit log integrity verified for {log_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify audit log integrity: {e}")
            return False


# Global audit logger instance
audit_logger = AuditLogger()


# Convenience functions
def log_security_event(service: str, user: str, action: str, outcome: str, 
                      details: Optional[Dict[str, Any]] = None, severity: str = "INFO") -> bool:
    """Log a security-related event"""
    return audit_logger.log_event("SECURITY", service, user, action, outcome, details, severity)


def log_trade_event(service: str, user: str, action: str, outcome: str, 
                   details: Optional[Dict[str, Any]] = None) -> bool:
    """Log a trading-related event"""
    return audit_logger.log_event("TRADE", service, user, action, outcome, details)


def log_auth_event(service: str, user: str, action: str, outcome: str, 
                  details: Optional[Dict[str, Any]] = None) -> bool:
    """Log an authentication-related event"""
    return audit_logger.log_event("AUTH", service, user, action, outcome, details)


def log_config_event(service: str, user: str, action: str, outcome: str, 
                    details: Optional[Dict[str, Any]] = None) -> bool:
    """Log a configuration-related event"""
    return audit_logger.log_event("CONFIG", service, user, action, outcome, details)