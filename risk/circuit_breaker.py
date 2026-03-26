"""
Circuit Breaker - Daily P&L based trading pause
"""
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    NORMAL = "normal"  # Trading allowed
    WARNING = "warning"  # Approaching limit
    TRIPPED = "tripped"  # Trading paused
    RESET = "reset"  # Ready for new day


@dataclass
class CircuitBreakerConfig:
    """Circuit Breaker Configuration"""
    daily_loss_limit_percent: float = 3.0  # 3% daily loss limit
    warning_threshold_percent: float = 2.0  # Warning at 2% loss
    max_trades_per_day: int = 50  # Max trades per day
    cooldown_minutes: int = 60  # Cooldown after tripping
    auto_reset_hour: int = 0  # Auto-reset at midnight (UTC)


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker event"""
    timestamp: float
    event_type: str  # "warning", "tripped", "reset", "trade"
    pnl_percent: float
    trades_count: int
    message: str


class CircuitBreaker:
    """
    Circuit Breaker - Auto-pause trading when daily loss threshold is hit
    
    This is CRITICAL for protecting your $10 account from blow-up
    """
    
    def __init__(self, config: CircuitBreakerConfig = None):
        """
        Initialize Circuit Breaker
        
        Args:
            config: CircuitBreakerConfig
        """
        self.config = config or CircuitBreakerConfig()
        
        self.state = CircuitBreakerState.NORMAL
        self.starting_balance: float = 0.0
        self.current_balance: float = 0.0
        
        self.daily_pnl: float = 0.0
        self.daily_pnl_percent: float = 0.0
        self.trades_today: int = 0
        
        self.tripped_at: Optional[float] = None
        self.warning_issued_at: Optional[float] = None
        
        self.events: List[CircuitBreakerEvent] = []
        self.daily_history: List[Dict] = []
        
        self._last_reset_date: Optional[str] = None
        
        logger.info(f"Circuit Breaker initialized: "
                   f"limit={self.config.daily_loss_limit_percent}%, "
                   f"warning={self.config.warning_threshold_percent}%, "
                   f"max_trades={self.config.max_trades_per_day}")
    
    def start_day(self, balance: float):
        """
        Start a new trading day
        
        Args:
            balance: Starting balance for the day
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Check if we need to reset for new day
        if self._last_reset_date != today:
            self._reset_for_new_day()
        
        self.starting_balance = balance
        self.current_balance = balance
        
        logger.info(f"Trading day started: ${balance:.2f}")
    
    def _reset_for_new_day(self):
        """Reset for a new trading day"""
        # Save yesterday's stats
        if self.daily_pnl != 0 or self.trades_today > 0:
            self.daily_history.append({
                'date': self._last_reset_date or datetime.utcnow().strftime("%Y-%m-%d"),
                'pnl': self.daily_pnl,
                'pnl_percent': self.daily_pnl_percent,
                'trades': self.trades_today,
                'ended_with': self.state.value,
            })
        
        # Reset state
        self.state = CircuitBreakerState.NORMAL
        self.daily_pnl = 0.0
        self.daily_pnl_percent = 0.0
        self.trades_today = 0
        self.tripped_at = None
        self.warning_issued_at = None
        
        self._last_reset_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        logger.info("Circuit breaker reset for new day")
    
    def update_balance(self, current_balance: float):
        """
        Update current balance and check circuit breaker
        
        Args:
            current_balance: Current account balance
        """
        self.current_balance = current_balance
        
        # Calculate daily PnL
        if self.starting_balance > 0:
            self.daily_pnl = current_balance - self.starting_balance
            self.daily_pnl_percent = (self.daily_pnl / self.starting_balance) * 100
        
        # Check limits
        self._check_limits()
    
    def record_trade(self, pnl: float) -> bool:
        """
        Record a trade and check if trading should continue
        
        Args:
            pnl: PnL from the trade
        
        Returns:
            True if trading can continue, False if circuit breaker tripped
        """
        # Update balance
        self.current_balance += pnl
        
        # Calculate daily PnL
        if self.starting_balance > 0:
            self.daily_pnl = self.current_balance - self.starting_balance
            self.daily_pnl_percent = (self.daily_pnl / self.starting_balance) * 100
        
        self.trades_today += 1
        
        # Log event
        event = CircuitBreakerEvent(
            timestamp=time.time(),
            event_type="trade",
            pnl_percent=self.daily_pnl_percent,
            trades_count=self.trades_today,
            message=f"Trade recorded: PnL ${pnl:.2f}, Daily: {self.daily_pnl_percent:.2f}%"
        )
        self.events.append(event)
        
        # Check limits
        self._check_limits()
        
        return self.state != CircuitBreakerState.TRIPPED
    
    def _check_limits(self):
        """Check circuit breaker limits"""
        # Check for new day reset
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._last_reset_date != today:
            self._reset_for_new_day()
        
        # Check daily loss limit
        if self.daily_pnl_percent <= -self.config.daily_loss_limit_percent:
            if self.state != CircuitBreakerState.TRIPPED:
                self._trip(f"Daily loss limit hit: {self.daily_pnl_percent:.2f}%")
        
        # Check warning threshold
        elif self.daily_pnl_percent <= -self.config.warning_threshold_percent:
            if self.state == CircuitBreakerState.NORMAL:
                self._warn(f"Warning: Daily loss approaching limit: {self.daily_pnl_percent:.2f}%")
        
        # Check max trades
        elif self.trades_today >= self.config.max_trades_per_day:
            if self.state == CircuitBreakerState.NORMAL:
                self._warn(f"Max daily trades reached: {self.trades_today}")
        
        # Check cooldown
        if self.state == CircuitBreakerState.TRIPPED and self.tripped_at:
            cooldown_end = self.tripped_at + (self.config.cooldown_minutes * 60)
            if time.time() >= cooldown_end:
                self._reset_after_cooldown()
    
    def _trip(self, reason: str):
        """Trip the circuit breaker"""
        self.state = CircuitBreakerState.TRIPPED
        self.tripped_at = time.time()
        
        event = CircuitBreakerEvent(
            timestamp=time.time(),
            event_type="tripped",
            pnl_percent=self.daily_pnl_percent,
            trades_count=self.trades_today,
            message=f"CIRCUIT TRIPPED: {reason}"
        )
        self.events.append(event)
        
        logger.critical(f"🚨 CIRCUIT BREAKER TRIPPED: {reason}")
        logger.critical(f"   Daily PnL: ${self.daily_pnl:.2f} ({self.daily_pnl_percent:.2f}%)")
        logger.critical(f"   Trades Today: {self.trades_today}")
        logger.critical(f"   Trading paused for {self.config.cooldown_minutes} minutes")
    
    def _warn(self, message: str):
        """Issue warning"""
        self.state = CircuitBreakerState.WARNING
        self.warning_issued_at = time.time()
        
        event = CircuitBreakerEvent(
            timestamp=time.time(),
            event_type="warning",
            pnl_percent=self.daily_pnl_percent,
            trades_count=self.trades_today,
            message=message
        )
        self.events.append(event)
        
        logger.warning(f"⚠️ {message}")
    
    def _reset_after_cooldown(self):
        """Reset circuit breaker after cooldown period"""
        self.state = CircuitBreakerState.NORMAL
        
        event = CircuitBreakerEvent(
            timestamp=time.time(),
            event_type="reset",
            pnl_percent=self.daily_pnl_percent,
            trades_count=self.trades_today,
            message="Circuit breaker reset after cooldown"
        )
        self.events.append(event)
        
        logger.info("✅ Circuit breaker reset - trading resumed")
    
    def force_reset(self):
        """Force reset circuit breaker (manual)"""
        old_state = self.state
        self.state = CircuitBreakerState.RESET
        
        event = CircuitBreakerEvent(
            timestamp=time.time(),
            event_type="reset",
            pnl_percent=self.daily_pnl_percent,
            trades_count=self.trades_today,
            message="Circuit breaker manually reset"
        )
        self.events.append(event)
        
        # Transition to normal
        self.state = CircuitBreakerState.NORMAL
        
        logger.warning(f"Circuit breaker manually reset (was: {old_state.value})")
    
    def can_trade(self) -> tuple[bool, str]:
        """
        Check if trading is allowed
        
        Returns:
            Tuple of (can_trade, reason)
        """
        # Check for new day reset
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._last_reset_date != today:
            self._reset_for_new_day()
        
        if self.state == CircuitBreakerState.TRIPPED:
            return False, f"Circuit breaker tripped. Cooldown: {self._get_cooldown_remaining()} minutes"
        
        if self.trades_today >= self.config.max_trades_per_day:
            return False, f"Max daily trades reached: {self.trades_today}"
        
        if self.daily_pnl_percent <= -self.config.daily_loss_limit_percent:
            return False, f"Daily loss limit exceeded: {self.daily_pnl_percent:.2f}%"
        
        return True, "Trading allowed"
    
    def _get_cooldown_remaining(self) -> int:
        """Get remaining cooldown time in minutes"""
        if not self.tripped_at:
            return 0
        
        elapsed = time.time() - self.tripped_at
        remaining = (self.config.cooldown_minutes * 60) - elapsed
        
        return max(0, int(remaining / 60))
    
    def get_status(self) -> Dict:
        """Get circuit breaker status"""
        can_trade, reason = self.can_trade()
        
        return {
            "state": self.state.value,
            "can_trade": can_trade,
            "reason": reason,
            "starting_balance": self.starting_balance,
            "current_balance": self.current_balance,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_percent": self.daily_pnl_percent,
            "trades_today": self.trades_today,
            "max_trades": self.config.max_trades_per_day,
            "loss_limit": self.config.daily_loss_limit_percent,
            "warning_threshold": self.config.warning_threshold_percent,
            "cooldown_remaining_minutes": self._get_cooldown_remaining(),
            "tripped_at": datetime.fromtimestamp(self.tripped_at).isoformat() if self.tripped_at else None,
        }
    
    def get_recent_events(self, count: int = 10) -> List[Dict]:
        """Get recent events"""
        events = self.events[-count:]
        return [
            {
                "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                "type": e.event_type,
                "pnl_percent": e.pnl_percent,
                "trades": e.trades_count,
                "message": e.message,
            }
            for e in events
        ]
    
    def get_today_summary(self) -> Dict:
        """Get today's trading summary"""
        return {
            "date": self._last_reset_date,
            "starting_balance": self.starting_balance,
            "current_balance": self.current_balance,
            "pnl": self.daily_pnl,
            "pnl_percent": self.daily_pnl_percent,
            "trades": self.trades_today,
            "state": self.state.value,
        }
    
    def get_daily_history(self, days: int = 30) -> List[Dict]:
        """Get daily history"""
        return self.daily_history[-days:]


def create_circuit_breaker(
    loss_limit_percent: float = 3.0,
    warning_percent: float = 2.0,
    max_trades: int = 50
) -> CircuitBreaker:
    """Create circuit breaker"""
    config = CircuitBreakerConfig(
        daily_loss_limit_percent=loss_limit_percent,
        warning_threshold_percent=warning_percent,
        max_trades_per_day=max_trades
    )
    return CircuitBreaker(config)
