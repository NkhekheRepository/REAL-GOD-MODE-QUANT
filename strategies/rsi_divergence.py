"""
RSI Divergence Strategy
RSI oversold/overbought + price divergence detection
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


@dataclass
class RSIData:
    """RSI calculation data"""
    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    
    rsi: float = 50.0
    prev_rsi: float = 50.0
    
    price: float = 0.0
    prev_price: float = 0.0
    
    divergence: str = "NONE"  # NONE, BULLISH, BEARISH


class RSIDivergenceStrategy:
    """
    RSI Divergence Strategy
    
    Buy when RSI shows bullish divergence (price lower low, RSI higher low)
    Sell when RSI shows bearish divergence (price higher high, RSI lower high)
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        divergence_lookback: int = 5
    ):
        """
        Initialize RSI Divergence Strategy
        
        Args:
            rsi_period: RSI period
            oversold: Oversold threshold
            overbought: Overbought threshold
            divergence_lookback: Lookback for divergence detection
        """
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.divergence_lookback = divergence_lookback
        
        self._prices: List[float] = []
        self._gains: List[float] = []
        self._losses: List[float] = []
        
        self._current_rsi: float = 50.0
        self._prev_rsi: float = 50.0
        
        self._last_signal: Signal = Signal.NEUTRAL
        self._signal_reason: str = ""
        
        logger.info(f"RSI Divergence Strategy initialized: period={rsi_period}, "
                   f"oversold={oversold}, overbought={overbought}")
    
    def update(self, price: float, volume: float = 0) -> Signal:
        """
        Update with new price and get signal
        
        Args:
            price: Current price
        
        Returns:
            Signal (BUY, SELL, NEUTRAL)
        """
        self._prices.append(price)
        
        # Keep enough data
        if len(self._prices) > self.rsi_period * 2:
            self._prices = self._prices[-(self.rsi_period * 2):]
        
        # Calculate RSI
        self._prev_rsi = self._current_rsi
        
        if len(self._prices) < 2:
            return Signal.NEUTRAL
        
        # Price change
        price_change = price - self._prices[-2]
        
        # Update gains/losses
        self._gains.append(max(price_change, 0))
        self._losses.append(max(-price_change, 0))
        
        if len(self._gains) > self.rsi_period:
            self._gains = self._gains[-self.rsi_period:]
            self._losses = self._losses[-self.rsi_period:]
        
        # Calculate RSI
        avg_gain = sum(self._gains) / self.rsi_period
        avg_loss = sum(self._losses) / self.rsi_period
        
        if avg_loss == 0:
            self._current_rsi = 100
        else:
            rs = avg_gain / avg_loss
            self._current_rsi = 100 - (100 / (1 + rs))
        
        # Detect divergence and generate signal
        signal = self._detect_signal(price)
        
        self._last_signal = signal
        
        return signal
    
    def _detect_signal(self, current_price: float) -> Signal:
        """Detect trading signal based on RSI and divergence"""
        
        # Check for oversold/overbought
        if self._current_rsi <= self.oversold:
            # Check for bullish divergence
            if self._check_bullish_divergence():
                self._signal_reason = f"RSI oversold ({self._current_rsi:.1f}) + bullish divergence"
                return Signal.BUY
        
        elif self._current_rsi >= self.overbought:
            # Check for bearish divergence
            if self._check_bearish_divergence():
                self._signal_reason = f"RSI overbought ({self._current_rsi:.1f}) + bearish divergence"
                return Signal.SELL
        
        # RSI extreme levels without divergence
        elif self._current_rsi < self.oversold + 5:
            self._signal_reason = f"RSI at {self._current_rsi:.1f} - near oversold"
            return Signal.BUY
        
        elif self._current_rsi > self.overbought - 5:
            self._signal_reason = f"RSI at {self._current_rsi:.1f} - near overbought"
            return Signal.SELL
        
        self._signal_reason = f"RSI neutral ({self._current_rsi:.1f})"
        return Signal.NEUTRAL
    
    def _check_bullish_divergence(self) -> bool:
        """Check for bullish price/RSI divergence"""
        if len(self._prices) < self.divergence_lookback * 2:
            return False
        
        # Look for: price making lower low, RSI making higher low
        recent_prices = self._prices[-self.divergence_lookback * 2:]
        
        # Find local minimums
        price_low_idx = self._find_local_min(recent_prices)
        
        if price_low_idx is None:
            return False
        
        # Check if price low is recent (more recent = stronger signal)
        if price_low_idx > len(recent_prices) // 2:
            return True
        
        return False
    
    def _check_bearish_divergence(self) -> bool:
        """Check for bearish price/RSI divergence"""
        if len(self._prices) < self.divergence_lookback * 2:
            return False
        
        recent_prices = self._prices[-self.divergence_lookback * 2:]
        
        # Find local maximums
        price_high_idx = self._find_local_max(recent_prices)
        
        if price_high_idx is None:
            return False
        
        if price_high_idx > len(recent_prices) // 2:
            return True
        
        return False
    
    def _find_local_min(self, data: List[float]) -> Optional[int]:
        """Find local minimum index"""
        if len(data) < 3:
            return None
        
        min_idx = 0
        min_val = data[0]
        
        for i in range(1, len(data)):
            if data[i] < min_val:
                min_val = data[i]
                min_idx = i
        
        return min_idx
    
    def _find_local_max(self, data: List[float]) -> Optional[int]:
        """Find local maximum index"""
        if len(data) < 3:
            return None
        
        max_idx = 0
        max_val = data[0]
        
        for i in range(1, len(data)):
            if data[i] > max_val:
                max_val = data[i]
                max_idx = i
        
        return max_idx
    
    def get_rsi(self) -> float:
        """Get current RSI"""
        return self._current_rsi
    
    def get_signal(self) -> Tuple[Signal, str]:
        """Get current signal and reason"""
        return self._last_signal, self._signal_reason
    
    def get_statistics(self) -> Dict:
        """Get strategy statistics"""
        return {
            "rsi": self._current_rsi,
            "signal": self._last_signal.value,
            "reason": self._signal_reason,
            "oversold": self.oversold,
            "overbought": self.overbought,
        }
    
    def reset(self):
        """Reset strategy state"""
        self._prices.clear()
        self._gains.clear()
        self._losses.clear()
        self._current_rsi = 50.0
        self._prev_rsi = 50.0
        self._last_signal = Signal.NEUTRAL
        logger.info("RSI Strategy reset")


def create_rsi_strategy(
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0
) -> RSIDivergenceStrategy:
    """Create RSI Divergence Strategy"""
    return RSIDivergenceStrategy(period, oversold, overbought)
