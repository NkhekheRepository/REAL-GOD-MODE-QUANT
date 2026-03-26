"""
Trust Scorer for vnpy-based God Mode Quant Trading Orchestrator
Implements dynamic trust scoring based on behavior, evidence chain integrity, and credential hygiene
"""
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

logger = logging.getLogger(__name__)


class TrustEventType(Enum):
    """Types of events that affect trust score"""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    TRADE_EXECUTED = "trade_executed"
    TRADE_FAILED = "trade_failed"
    CONFIG_CHANGE = "config_change"
    ACCESS_VIOLATION = "access_violation"
    CERTIFICATE_ROTATED = "certificate_rotated"
    SECRET_ACCESSED = "secret_accessed"
    ANOMALY_DETECTED = "anomaly_detected"
    COMPLIANCE_VIOLATION = "compliance_violation"


@dataclass
class TrustEvent:
    """A single trust-affecting event"""
    timestamp: float
    event_type: TrustEventType
    service: str
    user: str
    description: str
    weight: float = 1.0  # Positive for trust increase, negative for decrease
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "service": self.service,
            "user": self.user,
            "description": self.description,
            "weight": self.weight,
            "metadata": self.metadata
        }


@dataclass
class TrustScore:
    """Trust score for a service or user"""
    service_or_user: str
    score: float = 100.0  # Start with perfect score
    min_score: float = 0.0
    max_score: float = 100.0
    last_updated: float = field(default_factory=time.time)
    decay_factor: float = 0.99  # Daily decay factor
    events: List[TrustEvent] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_or_user": self.service_or_user,
            "score": self.score,
            "min_score": self.min_score,
            "max_score": self.max_score,
            "last_updated": self.last_updated,
            "decay_factor": self.decay_factor,
            "events": [event.to_dict() for event in self.events[-50:]]  # Last 50 events
        }


class TrustScorer:
    """Dynamic trust scoring system"""
    
    def __init__(self):
        self.scores: Dict[str, TrustScore] = {}
        self.decay_factor = 0.99  # Daily decay factor
        self.event_weights = {
            TrustEventType.AUTH_SUCCESS: 2.0,
            TrustEventType.AUTH_FAILURE: -10.0,
            TrustEventType.TRADE_EXECUTED: 0.5,
            TrustEventType.TRADE_FAILED: -5.0,
            TrustEventType.CONFIG_CHANGE: -2.0,
            TrustEventType.ACCESS_VIOLATION: -20.0,
            TrustEventType.CERTIFICATE_ROTATED: 5.0,
            TrustEventType.SECRET_ACCESSED: 0.1,
            TrustEventType.ANOMALY_DETECTED: -15.0,
            TrustEventType.COMPLIANCE_VIOLATION: -25.0
        }
        
    def _apply_decay(self, trust_score: TrustScore):
        """Apply time-based decay to trust score"""
        hours_passed = (time.time() - trust_score.last_updated) / 3600
        if hours_passed > 0:
            # Apply decay based on hours passed
            decay = self.decay_factor ** (hours_passed / 24)  # Daily decay
            trust_score.score = (
                trust_score.min_score + 
                (trust_score.score - trust_score.min_score) * decay
            )
            trust_score.last_updated = time.time()
    
    def get_trust_score(self, service_or_user: str) -> float:
        """Get current trust score for a service or user"""
        if service_or_user not in self.scores:
            # Initialize new trust score
            self.scores[service_or_user] = TrustScore(service_or_user=service_or_user)
        
        trust_score = self.scores[service_or_user]
        self._apply_decay(trust_score)
        return trust_score.score
    
    def record_event(self, service_or_user: str, event_type: TrustEventType, 
                    service: str, user: str, description: str,
                    custom_weight: Optional[float] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Record a trust-affecting event
        
        Args:
            service_or_user: The service or user this event affects
            event_type: Type of event
            service: Service generating the event
            user: User or service account
            description: Human-readable description
            custom_weight: Override default weight for this event
            metadata: Additional event data
            
        Returns:
            True if event was recorded successfully
        """
        try:
            if service_or_user not in self.scores:
                self.scores[service_or_user] = TrustScore(service_or_user=service_or_user)
            
            trust_score = self.scores[service_or_user]
            
            # Apply decay before adding new event
            self._apply_decay(trust_score)
            
            # Determine weight
            weight = custom_weight if custom_weight is not None else self.event_weights.get(event_type, 0.0)
            
            # Create event
            event = TrustEvent(
                timestamp=time.time(),
                event_type=event_type,
                service=service,
                user=user,
                description=description,
                weight=weight,
                metadata=metadata or {}
            )
            
            # Update score
            trust_score.score += weight
            
            # Clamp score to valid range
            trust_score.score = max(
                trust_score.min_score, 
                min(trust_score.max_score, trust_score.score)
            )
            
            # Add event to history (keep last 1000 events)
            trust_score.events.append(event)
            if len(trust_score.events) > 1000:
                trust_score.events = trust_score.events[-1000:]
            
            trust_score.last_updated = time.time()
            
            logger.info(
                f"Trust event recorded for {service_or_user}: {event_type.value} "
                f"(weight: {weight:+.1f}, new score: {trust_score.score:.1f})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record trust event: {e}")
            return False
    
    def get_trust_report(self, service_or_user: str) -> Dict[str, Any]:
        """Get detailed trust report for a service or user"""
        if service_or_user not in self.scores:
            return {"error": "No trust data found"}
        
        trust_score = self.scores[service_or_user]
        self._apply_decay(trust_score)
        
        # Calculate recent trends
        recent_events = [
            e for e in trust_score.events 
            if time.time() - e.timestamp < 3600 * 24  # Last 24 hours
        ]
        
        recent_weight = sum(e.weight for e in recent_events)
        
        return {
            "service_or_user": service_or_user,
            "current_score": trust_score.score,
            "score_range": [trust_score.min_score, trust_score.max_score],
            "last_updated": trust_score.last_updated,
            "recent_24h_weight": recent_weight,
            "recent_events_count": len(recent_events),
            "total_events": len(trust_score.events),
            "is_trustworthy": trust_score.score > 70.0,  # Configurable threshold
            "needs_attention": trust_score.score < 50.0  # Configurable threshold
        }


# Global trust scorer instance
trust_scorer = TrustScorer()


# Convenience functions
def record_trust_event(service_or_user: str, event_type: TrustEventType, 
                      service: str, user: str, description: str,
                      custom_weight: Optional[float] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Record a trust-affecting event"""
    return trust_scorer.record_event(
        service_or_user, event_type, service, user, description, 
        custom_weight, metadata
    )


def get_trust_score(service_or_user: str) -> float:
    """Get current trust score for a service or user"""
    return trust_scorer.get_trust_score(service_or_user)


def get_trust_report(service_or_user: str) -> Dict[str, Any]:
    """Get detailed trust report for a service or user"""
    return trust_scorer.get_trust_report(service_or_user)


# Predefined event recorders for common scenarios
def record_auth_success(service: str, user: str, metadata: Optional[Dict[str, Any]] = None):
    """Record successful authentication"""
    return record_trust_event(
        service_or_user=f"{service}:{user}",
        event_type=TrustEventType.AUTH_SUCCESS,
        service=service,
        user=user,
        description="Successful authentication",
        metadata=metadata
    )


def record_auth_failure(service: str, user: str, metadata: Optional[Dict[str, Any]] = None):
    """Record failed authentication"""
    return record_trust_event(
        service_or_user=f"{service}:{user}",
        event_type=TrustEventType.AUTH_FAILURE,
        service=service,
        user=user,
        description="Failed authentication attempt",
        metadata=metadata
    )


def record_trade_executed(service: str, user: str, symbol: str, 
                         metadata: Optional[Dict[str, Any]] = None):
    """Record successful trade execution"""
    trade_metadata = metadata or {}
    trade_metadata.update({"symbol": symbol})
    
    return record_trust_event(
        service_or_user=f"{service}:{user}",
        event_type=TrustEventType.TRADE_EXECUTED,
        service=service,
        user=user,
        description=f"Trade executed: {symbol}",
        metadata=trade_metadata
    )


def record_access_violation(service: str, user: str, resource: str,
                           metadata: Optional[Dict[str, Any]] = None):
    """Record access violation"""
    violation_metadata = metadata or {}
    violation_metadata.update({"resource": resource})
    
    return record_trust_event(
        service_or_user=f"{service}:{user}",
        event_type=TrustEventType.ACCESS_VIOLATION,
        service=service,
        user=user,
        description=f"Access violation: {resource}",
        metadata=violation_metadata
    )


def record_certificate_rotated(service: str, metadata: Optional[Dict[str, Any]] = None):
    """Record certificate rotation"""
    return record_trust_event(
        service_or_user=service,
        event_type=TrustEventType.CERTIFICATE_ROTATED,
        service=service,
        user="system",
        description="Certificate rotated",
        metadata=metadata
    )


def record_secret_accessed(service: str, user: str, secret_path: str,
                          metadata: Optional[Dict[str, Any]] = None):
    """Record secret access"""
    access_metadata = metadata or {}
    access_metadata.update({"secret_path": secret_path})
    
    return record_trust_event(
        service_or_user=f"{service}:{user}",
        event_type=TrustEventType.SECRET_ACCESSED,
        service=service,
        user=user,
        description=f"Secret accessed: {secret_path}",
        metadata=access_metadata
    )