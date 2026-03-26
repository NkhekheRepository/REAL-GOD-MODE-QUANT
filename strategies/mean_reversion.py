"""
Mean Reversion Strategy
Price reverts to moving average with overbought/oversold signals
"""
import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


@dataclass
class MeanReversionData:
    """Mean reversion data"""
    ma: float
    price: float
    deviation: float  # % deviation from MA
    z_score: float
    bands_upper: float
    bands_lower: float


class MeanReversionStrategy:
    """
    Mean Reversion Strategy
    
    Buy when price is oversold relative to MA
    Sell when price is overbought relative to MA
    Uses standard deviation bands around MA
    """
    
    def __init__(
        self,
        ma_period: int = 20,
        std_dev_multiplier: float = 2.0,
        deviation_threshold: float = 2.0,  # % deviation for signal
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70
    ):
        """
        Initialize Mean Reversion Strategy
        
        Args:
            ma_period: Moving average period
            std_dev_multiplier: Standard deviations for bands
            deviation_threshold: % deviation for signal
            rsi_period: RSI period
            rsi_oversold: RSI oversold level
            rsi_overbought: RSI overbought level
        """
        self.ma_period = ma_period
        self.std_dev_multiplier = std_dev_multiplier
        self.deviation_threshold = deviation_threshold
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        
        self._prices: deque = deque(maxlen=ma_period * 2)
        self._volumes: deque = deque(maxlen=ma_period * 2)
        
        self._current_data: Optional[MeanReversionData] = None
        self._last_signal: Signal = Signal.NEUTRAL
        self._signal_reason: str = ""
        
        self._rsi_values: List[float] = []
        
        logger.info(f"Mean Reversion Strategy initialized: ma_period={ma_period}")
    
    def update(self, price: float, volume: float = 0) -> Signal:
        """
        Update with new price and volume
        
        Args:
            price: Current price
            volume: Current volume
        
        Returns:
            Signal (BUY, SELL, NEUTRAL)
        """
        self._prices.append(price)
        self._volumes.append(volume)
        
        # Need enough data
        if len(self._prices) < self.ma_period:
            return Signal.NEUTRAL
        
        # Calculate mean reversion data
        data = self._calculate()
        self._current_data = data
        
        # Calculate RSI
        self._update_rsi(price)
        
        # Detect signal
        signal = self._detect_signal(price)
        
        self._last_signal = signal
        
        return signal
    
    def _calculate(self) -> MeanReversionData:
        """Calculate mean reversion indicators"""
        prices = list(self._prices)[-self.ma_period:]
        
        # Moving average
        ma = sum(prices) / len(prices)
        
        # Standard deviation
        variance = sum((p - ma) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance)
        
        # Bands
        bands_upper = ma + (self.std_dev_multiplier * std)
        bands_lower = ma - (self.std_dev_multiplier * std)
        
        # Current price
        current_price = self._prices[-1]
        
        # Deviation from MA
        deviation = ((current_price - ma) / ma) * 100 if ma > 0 else 0
        
        # Z-score
        z_score = (current_price - ma) / std if std > 0 else 0
        
        return MeanReversionData(
            ma=ma,
            price=current_price,
            deviation=deviation,
            z_score=z_score,
            bands_upper=bands_upper,
            bands_lower=bands_lower
        )
    
    def _update_rsi(self, price: float):
        """Update RSI values"""
        prices = list(self._prices)
        
        if len(prices) < 2:
            return
        
        # Price change
        change = price - prices[-2]
        
        if change > 0:
            self._rsi_values.append(change)
            if len(self._rsi_values) > 1 and len(self._rsi_values) > self.rsi_period:
                self._rsi_values = self._rsi_values[-self.rsi_period:]
        else:
            if len(self._rsi_values) > 0:
                self._rsi_values[-1] = max(self._rsi_values[-1], abs(change))
            else:
                self._rsi_values.append(abs(change))
    
    def _get_rsi(self) -> float:
        """Get current RSI"""
        if len(self._rsi_values) < self.rsi_period:
            return 50.0
        
        gains = sum(self._rsi_values[-self.rsi_period:]) / self.rsi_period
        
        if gains == 0:
            return 100.0
        
        return min(100, gains * 10)  # Simplified
    
    def _detect_signal(self, price: float) -> Signal:
        """Detect mean reversion signal"""
        
        data = self._current_data
        if data is None:
            return Signal.NEUTRAL
        
        rsi = self._get_rsi()
        
        # BUY conditions (price oversold, expect reversion up)
        if data.deviation < -self.deviation_threshold:
            self._signal_reason = f"OVERSOLD: price {data.deviation:.1f}% below MA (${data.ma:.2f})"
            return Signal.BUY
        
        if data.z_score < -2:
            self._signal_reason = f"EXTREME DEVIATION: z-score {data.z_score:.2f}"
            return Signal.BUY
        
        if rsi < self.rsi_oversold:
            self._signal_reason = f"RSI oversold ({rsi:.1f})"
            return Signal.BUY
        
        # Price near lower band
        if price < data.bands_lower:
            self._signal_reason = f"Below lower band - potential mean reversion"
            return Signal.BUY
        
        # SELL conditions (price overbought, expect reversion down)
        if data.deviation > self.deviation_threshold:
            self._signal_reason = f"OVERBOUGHT: price {data.deviation:.1f}% above MA (${data.ma:.2f})"
            return Signal.SELL
        
        if data.z_score > 2:
            self._signal_reason = f"EXTREME DEVIATION: z-score {data.z_score:.2f}"
            return Signal.SELL
        
        if rsi > self.rsi_overbought:
            self._signal_reason = f"RSI overbought ({rsi:.1f})"
            return Signal.SELL
        
        # Price near upper band
        if price > data.bands_upper:
            self._signal_reason = f"Above upper band - potential mean reversion"
            return Signal.SELL
        
        # Neutral
        self._signal_reason = f"Price near MA (deviation: {data.deviation:.1f}%)"
        return Signal.NEUTRAL
    
    def get_data(self) -> Optional[MeanReversionData]:
        """Get current mean reversion data"""
        return self._current_data
    
    def get_signal(self) -> Tuple[Signal, str]:
        """Get current signal and reason"""
        return self._last_signal, self._signal_reason
    
    def get_statistics(self) -> Dict:
        """Get strategy statistics"""
        data = self._current_data
        
        return {
            "signal": self._last_signal.value,
            "reason": self._signal_reason,
            "ma": data.ma if data else 0,
            "deviation": data.deviation if data else 0,
            "z_score": data.z_score if data else 0,
            "upper_band": data.bands_upper if data else 0,
            "lower_band": data.bands_lower if data else 0,
        }
    
    def reset(self):
        """Reset strategy state"""
        self._prices.clear()
        self._volumes.clear()
        self._rsi_values.clear()
        self._current_data = None
        self._last_signal = Signal.NEUTRAL
        logger.info("Mean Reversion Strategy reset")


def create_mean_reversion_strategy(
    ma_period: int = 20,
    deviation_threshold: float = 2.0
) -> MeanReversionStrategy:
    """Create Mean Reversion Strategy"""
    return MeanReversionStrategy(ma_period, deviation_threshold)
