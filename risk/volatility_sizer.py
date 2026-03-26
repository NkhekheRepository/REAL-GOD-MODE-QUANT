"""
Volatility-Based Position Sizing
Adjust position size based on market volatility
"""
import time
import math
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


class ATRCalculator:
    """Average True Range Calculator"""
    
    def __init__(self, period: int = 14):
        self.period = period
        self._prices: deque = deque(maxlen=period + 1)
        self._trs: List[float] = []
    
    def update(self, high: float, low: float, close: float) -> float:
        """Update with new candle and return ATR"""
        self._prices.append((high, low, close))
        
        if len(self._prices) < 2:
            return 0.0
        
        # Calculate True Range
        prev_high, prev_low, prev_close = self._prices[-2]
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        tr = max(tr1, tr2, tr3)
        
        self._trs.append(tr)
        
        if len(self._trs) < self.period:
            return sum(self._trs) / len(self._trs) if self._trs else 0.0
        
        # ATR = Simple moving average of TR
        atr = sum(self._trs[-self.period:]) / self.period
        
        return atr
    
    def get_atr(self) -> float:
        """Get current ATR"""
        if not self._trs:
            return 0.0
        if len(self._trs) < self.period:
            return sum(self._trs) / len(self._trs)
        return sum(self._trs[-self.period:]) / self.period
    
    def get_atr_percent(self, current_price: float) -> float:
        """Get ATR as percentage of price"""
        atr = self.get_atr()
        if current_price <= 0:
            return 0.0
        return (atr / current_price) * 100


@dataclass
class VolatilityMetrics:
    """Volatility metrics"""
    atr: float
    atr_percent: float
    volatility_regime: str  # LOW, NORMAL, HIGH, EXTREME
    position_multiplier: float
    recommended_risk_percent: float


class VolatilitySizer:
    """
    Volatility-Based Position Sizer
    
    Reduces position size when volatility spikes to prevent large losses
    """
    
    def __init__(
        self,
        base_risk_percent: float = 1.0,
        atr_period: int = 14,
        volatility_multipliers: Dict[str, float] = None
    ):
        """
        Initialize Volatility Sizer
        
        Args:
            base_risk_percent: Base risk percentage for normal volatility
            atr_period: Period for ATR calculation
            volatility_multipliers: Risk multipliers per regime
        """
        self.base_risk_percent = base_risk_percent
        self.atr_calculator = ATRCalculator(atr_period)
        
        # Default volatility regime multipliers
        self.volatility_multipliers = volatility_multipliers or {
            "LOW": 1.5,      # More aggressive in low volatility
            "NORMAL": 1.0,   # Normal risk
            "HIGH": 0.5,     # Reduce risk in high volatility
            "EXTREME": 0.25, # Very conservative in extreme volatility
        }
        
        # Thresholds (ATR %)
        self.low_threshold = 0.5    # Below 0.5% = LOW
        self.normal_threshold = 1.0 # 0.5-1.0% = NORMAL
        self.high_threshold = 2.0   # 1.0-2.0% = HIGH
        # Above 2.0% = EXTREME
        
        self._atr_history: List[float] = []
        self._volatility_history: List[Dict] = []
        
        logger.info(f"Volatility Sizer initialized: base_risk={base_risk_percent}%")
    
    def update(self, high: float, low: float, close: float, volume: float = 0) -> VolatilityMetrics:
        """
        Update with new candle data
        
        Args:
            high: High price
            low: Low price
            close: Close price
            volume: Volume (optional)
        
        Returns:
            VolatilityMetrics
        """
        atr = self.atr_calculator.update(high, low, close)
        atr_percent = self.atr_calculator.get_atr_percent(close)
        
        # Determine volatility regime
        regime = self._get_volatility_regime(atr_percent)
        
        # Get multiplier
        multiplier = self.volatility_multipliers.get(regime, 1.0)
        
        # Calculate adjusted risk
        adjusted_risk = self.base_risk_percent * multiplier
        
        # Store history
        self._atr_history.append(atr)
        self._volatility_history.append({
            'timestamp': time.time(),
            'atr': atr,
            'atr_percent': atr_percent,
            'regime': regime,
            'multiplier': multiplier,
            'risk_percent': adjusted_risk,
        })
        
        # Keep only last 1000 entries
        if len(self._volatility_history) > 1000:
            self._volatility_history = self._volatility_history[-1000:]
        
        return VolatilityMetrics(
            atr=atr,
            atr_percent=atr_percent,
            volatility_regime=regime,
            position_multiplier=multiplier,
            recommended_risk_percent=adjusted_risk
        )
    
    def _get_volatility_regime(self, atr_percent: float) -> str:
        """Determine volatility regime"""
        if atr_percent < self.low_threshold:
            return "LOW"
        elif atr_percent < self.normal_threshold:
            return "NORMAL"
        elif atr_percent < self.high_threshold:
            return "HIGH"
        else:
            return "EXTREME"
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        portfolio_value: float,
        atr_percent: float = None
    ) -> float:
        """
        Calculate position size based on volatility
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            portfolio_value: Portfolio value
            atr_percent: Current ATR percent (optional)
        
        Returns:
            Position size (quantity)
        """
        # Use provided ATR or get current
        if atr_percent is None:
            atr_percent = self.atr_calculator.get_atr_percent(entry_price)
        
        # Determine regime and multiplier
        regime = self._get_volatility_regime(atr_percent)
        multiplier = self.volatility_multipliers.get(regime, 1.0)
        
        # Adjust risk
        risk_percent = self.base_risk_percent * multiplier
        
        # Risk amount
        risk_amount = portfolio_value * (risk_percent / 100)
        
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share <= 0:
            logger.warning("Stop loss too tight")
            return 0.0
        
        # Calculate position size
        position_size = risk_amount / risk_per_share
        
        logger.info(f"Volatility position: {position_size:.4f} @ ${entry_price:.2f} "
                   f"(regime: {regime}, risk: {risk_percent:.2f}%, "
                   f"atr: {atr_percent:.2f}%)")
        
        return position_size
    
    def get_volatility_regime(self, atr_percent: float = None) -> str:
        """Get current volatility regime"""
        if atr_percent is None:
            atr_percent = self.atr_calculator.get_atr_percent(
                self._atr_history[-1] if self._atr_history else 0
            )
        return self._get_volatility_regime(atr_percent)
    
    def get_multiplier(self, regime: str = None) -> float:
        """Get multiplier for regime"""
        if regime is None:
            regime = self.get_volatility_regime()
        return self.volatility_multipliers.get(regime, 1.0)
    
    def is_safe_to_trade(self, atr_percent: float = None) -> tuple[bool, str]:
        """
        Check if it's safe to trade based on volatility
        
        Returns:
            Tuple of (is_safe, reason)
        """
        if atr_percent is None:
            atr_percent = self.atr_calculator.get_atr_percent(
                self._atr_history[-1] if self._atr_history else 0
            )
        
        regime = self._get_volatility_regime(atr_percent)
        
        if regime == "EXTREME":
            return False, f"Extreme volatility (ATR: {atr_percent:.2f}%) - too risky"
        
        if regime == "HIGH":
            return True, f"High volatility (ATR: {atr_percent:.2f}%) - reduced position size"
        
        return True, f"Normal volatility (ATR: {atr_percent:.2f}%)"
    
    def get_statistics(self) -> Dict:
        """Get volatility statistics"""
        current_atr = self.atr_calculator.get_atr()
        
        if self._atr_history:
            avg_atr = sum(self._atr_history) / len(self._atr_history)
            max_atr = max(self._atr_history)
            min_atr = min(self._atr_history)
        else:
            avg_atr = max_atr = min_atr = 0
        
        return {
            "current_atr": current_atr,
            "average_atr": avg_atr,
            "max_atr": max_atr,
            "min_atr": min_atr,
            "current_regime": self.get_volatility_regime(),
            "base_risk_percent": self.base_risk_percent,
            "multipliers": self.volatility_multipliers,
        }
    
    def get_recent_volatility(self, count: int = 20) -> List[Dict]:
        """Get recent volatility data"""
        return self._volatility_history[-count:]


def create_volatility_sizer(
    base_risk_percent: float = 1.0,
    atr_period: int = 14
) -> VolatilitySizer:
    """Create volatility sizer"""
    return VolatilitySizer(base_risk_percent, atr_period)
