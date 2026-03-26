"""
Bollinger Bands Breakout Strategy
Price breakout from Bollinger Bands with volume confirmation
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
class BollingerData:
    """Bollinger Bands data"""
    upper: float
    middle: float
    lower: float
    bandwidth: float
    position: float  # Price position relative to bands


class BollingerBreakoutStrategy:
    """
    Bollinger Bands Breakout Strategy
    
    Buy when price breaks above upper band with volume
    Sell when price breaks below lower band with volume
    """
    
    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        volume_confirmation: bool = True,
        volume_threshold: float = 1.5
    ):
        """
        Initialize Bollinger Breakout Strategy
        
        Args:
            period: Moving average period
            std_dev: Standard deviations for bands
            volume_confirmation: Require volume spike for signal
            volume_threshold: Volume multiplier threshold
        """
        self.period = period
        self.std_dev = std_dev
        self.volume_confirmation = volume_confirmation
        self.volume_threshold = volume_threshold
        
        self._prices: deque = deque(maxlen=period + 1)
        self._volumes: deque = deque(maxlen=period + 1)
        
        self._current_bollinger: Optional[BollingerData] = None
        self._last_signal: Signal = Signal.NEUTRAL
        self._signal_reason: str = ""
        
        self._avg_volume: float = 0.0
        
        logger.info(f"Bollinger Breakout Strategy initialized: period={period}, "
                   f"std_dev={std_dev}")
    
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
        
        if len(self._prices) < self.period:
            return Signal.NEUTRAL
        
        # Calculate Bollinger Bands
        bb = self._calculate_bollinger()
        self._current_bollinger = bb
        
        # Calculate average volume
        if len(self._volumes) >= self.period:
            self._avg_volume = sum(list(self._volumes)[-self.period:]) / self.period
        
        # Detect breakout
        signal = self._detect_breakout(price, volume)
        
        self._last_signal = signal
        
        return signal
    
    def _calculate_bollinger(self) -> BollingerData:
        """Calculate Bollinger Bands"""
        prices = list(self._prices)[-self.period:]
        
        # Middle band (SMA)
        middle = sum(prices) / len(prices)
        
        # Standard deviation
        variance = sum((p - middle) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance)
        
        # Bands
        upper = middle + (self.std_dev * std)
        lower = middle - (self.std_dev * std)
        
        # Bandwidth
        bandwidth = (upper - lower) / middle * 100 if middle > 0 else 0
        
        # Current price position
        current_price = self._prices[-1]
        if upper != lower:
            position = (current_price - lower) / (upper - lower) * 100
        else:
            position = 50
        
        return BollingerData(
            upper=upper,
            middle=middle,
            lower=lower,
            bandwidth=bandwidth,
            position=position
        )
    
    def _detect_breakout(self, price: float, volume: float) -> Signal:
        """Detect breakout signal"""
        
        bb = self._current_bollinger
        if bb is None:
            return Signal.NEUTRAL
        
        # Check volume confirmation
        volume_ok = True
        if self.volume_confirmation and volume > 0 and self._avg_volume > 0:
            volume_ratio = volume / self._avg_volume
            volume_ok = volume_ratio >= self.volume_threshold
        
        # Buy signal: Price breaks above upper band
        if price > bb.upper:
            if volume_ok:
                self._signal_reason = f"Breakout ABOVE upper band (${bb.upper:.2f}) with volume"
                return Signal.BUY
            else:
                self._signal_reason = f"Price above upper band but low volume"
        
        # Sell signal: Price breaks below lower band
        elif price < bb.lower:
            if volume_ok:
                self._signal_reason = f"Breakout BELOW lower band (${bb.lower:.2f}) with volume"
                return Signal.SELL
            else:
                self._signal_reason = f"Price below lower band but low volume"
        
        # Near upper band - potential buy
        elif bb.position > 90:
            self._signal_reason = f"Price near upper band (BB position: {bb.position:.1f}%)"
            return Signal.BUY
        
        # Near lower band - potential sell
        elif bb.position < 10:
            self._signal_reason = f"Price near lower band (BB position: {bb.position:.1f}%)"
            return Signal.SELL
        
        # Trend continuation - price above middle and trending up
        elif price > bb.middle and self._prices[-1] > self._prices[-2]:
            if volume_ok:
                self._signal_reason = f"Uptrend continuation (above middle band)"
                return Signal.BUY
        
        # Downtrend continuation - price below middle and trending down
        elif price < bb.middle and self._prices[-1] < self._prices[-2]:
            if volume_ok:
                self._signal_reason = f"Downtrend continuation (below middle band)"
                return Signal.SELL
        
        self._signal_reason = f"Price within bands (BB position: {bb.position:.1f}%)"
        return Signal.NEUTRAL
    
    def get_bollinger_bands(self) -> Optional[BollingerData]:
        """Get current Bollinger Bands"""
        return self._current_bollinger
    
    def get_signal(self) -> Tuple[Signal, str]:
        """Get current signal and reason"""
        return self._last_signal, self._signal_reason
    
    def get_statistics(self) -> Dict:
        """Get strategy statistics"""
        bb = self._current_bollinger
        
        return {
            "signal": self._last_signal.value,
            "reason": self._signal_reason,
            "upper": bb.upper if bb else 0,
            "middle": bb.middle if bb else 0,
            "lower": bb.lower if bb else 0,
            "bandwidth": bb.bandwidth if bb else 0,
            "position": bb.position if bb else 0,
            "avg_volume": self._avg_volume,
        }
    
    def reset(self):
        """Reset strategy state"""
        self._prices.clear()
        self._volumes.clear()
        self._current_bollinger = None
        self._last_signal = Signal.NEUTRAL
        self._avg_volume = 0.0
        logger.info("Bollinger Strategy reset")


def create_bollinger_strategy(
    period: int = 20,
    std_dev: float = 2.0
) -> BollingerBreakoutStrategy:
    """Create Bollinger Breakout Strategy"""
    return BollingerBreakoutStrategy(period, std_dev)
