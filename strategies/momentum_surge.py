"""
Momentum Surge Strategy
High momentum + volume confirmation strategy
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
class MomentumData:
    """Momentum data"""
    rsi: float
    momentum: float
    roc: float  # Rate of change
    volume_ratio: float
    trend_strength: float


class MomentumSurgeStrategy:
    """
    Momentum Surge Strategy
    
    Buy when multiple momentum indicators align with volume surge
    Sell when momentum weakens
    """
    
    def __init__(
        self,
        lookback_period: int = 14,
        rsi_period: int = 14,
        momentum_period: int = 10,
        roc_period: int = 12,
        volume_ma_period: int = 20,
        momentum_threshold: float = 0.03,
        volume_threshold: float = 1.5
    ):
        """
        Initialize Momentum Surge Strategy
        
        Args:
            lookback_period: General lookback
            rsi_period: RSI period
            momentum_period: Momentum period
            roc_period: Rate of change period
            volume_ma_period: Volume moving average period
            momentum_threshold: Minimum momentum for signal
            volume_threshold: Volume multiplier for confirmation
        """
        self.lookback_period = lookback_period
        self.rsi_period = rsi_period
        self.momentum_period = momentum_period
        self.roc_period = roc_period
        self.volume_ma_period = volume_ma_period
        self.momentum_threshold = momentum_threshold
        self.volume_threshold = volume_threshold
        
        self._prices: deque = deque(maxlen=lookback_period + 1)
        self._volumes: deque = deque(maxlen=lookback_period + 1)
        
        self._gains: List[float] = []
        self._losses: List[float] = []
        
        self._current_momentum: Optional[MomentumData] = None
        self._last_signal: Signal = Signal.NEUTRAL
        self._signal_reason: str = ""
        
        logger.info(f"Momentum Surge Strategy initialized")
    
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
        if len(self._prices) < max(self.lookback_period, self.rsi_period, self.volume_ma_period):
            return Signal.NEUTRAL
        
        # Calculate momentum
        momentum = self._calculate_momentum()
        self._current_momentum = momentum
        
        # Detect signal
        signal = self._detect_signal(price, volume)
        
        self._last_signal = signal
        
        return signal
    
    def _calculate_momentum(self) -> MomentumData:
        """Calculate all momentum indicators"""
        
        prices = list(self._prices)
        volumes = list(self._volumes)
        
        # RSI
        rsi = self._calculate_rsi()
        
        # Momentum (current price - price N periods ago)
        if len(prices) > self.momentum_period:
            momentum = (prices[-1] - prices[-self.momentum_period-1]) / prices[-self.momentum_period-1]
        else:
            momentum = 0.0
        
        # Rate of Change
        if len(prices) > self.roc_period:
            roc = (prices[-1] - prices[-self.roc_period-1]) / prices[-self.roc_period-1]
        else:
            roc = 0.0
        
        # Volume ratio
        if len(volumes) >= self.volume_ma_period and sum(volumes[-self.volume_ma_period:]) > 0:
            recent_volume = sum(volumes[-5:]) / 5
            avg_volume = sum(volumes[-self.volume_ma_period:]) / self.volume_ma_period
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        else:
            volume_ratio = 1.0
        
        # Trend strength (based on consecutive closes)
        trend_strength = self._calculate_trend_strength()
        
        return MomentumData(
            rsi=rsi,
            momentum=momentum,
            roc=roc,
            volume_ratio=volume_ratio,
            trend_strength=trend_strength
        )
    
    def _calculate_rsi(self) -> float:
        """Calculate RSI"""
        prices = list(self._prices)
        
        if len(prices) < self.rsi_period + 1:
            return 50.0
        
        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Use last rsi_period changes
        recent_changes = changes[-self.rsi_period:]
        
        gains = [max(c, 0) for c in recent_changes]
        losses = [max(-c, 0) for c in recent_changes]
        
        avg_gain = sum(gains) / self.rsi_period
        avg_loss = sum(losses) / self.rsi_period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_trend_strength(self) -> float:
        """Calculate trend strength (0-100)"""
        prices = list(self._prices)
        
        if len(prices) < 5:
            return 50.0
        
        # Count consecutive up closes
        up_count = 0
        for i in range(len(prices) - 4, len(prices)):
            if prices[i] > prices[i-1]:
                up_count += 1
        
        # Normalize to 0-100
        return (up_count / 4) * 100
    
    def _detect_signal(self, price: float, volume: float) -> Signal:
        """Detect momentum surge signal"""
        
        m = self._current_momentum
        if m is None:
            return Signal.NEUTRAL
        
        # BUY conditions:
        # 1. RSI < 50 (not overbought) AND momentum positive
        # 2. Volume spike
        # 3. Strong uptrend
        
        buy_score = 0
        
        if m.rsi < 65 and m.rsi > 35:
            buy_score += 1
        elif m.rsi < 50:
            buy_score += 2
        
        if m.momentum > self.momentum_threshold:
            buy_score += 2
        elif m.momentum > 0:
            buy_score += 1
        
        if m.roc > self.momentum_threshold:
            buy_score += 2
        
        if m.volume_ratio > self.volume_threshold:
            buy_score += 2
        elif m.volume_ratio > 1.0:
            buy_score += 1
        
        if m.trend_strength > 75:
            buy_score += 2
        elif m.trend_strength > 50:
            buy_score += 1
        
        # SELL conditions
        sell_score = 0
        
        if m.rsi > 55:
            sell_score += 1
        if m.rsi > 70:
            sell_score += 2
        
        if m.momentum < -self.momentum_threshold:
            sell_score += 2
        elif m.momentum < 0:
            sell_score += 1
        
        if m.roc < -self.momentum_threshold:
            sell_score += 2
        
        if m.trend_strength < 25:
            sell_score += 2
        elif m.trend_strength < 50:
            sell_score += 1
        
        # Determine signal
        if buy_score >= 6:
            self._signal_reason = f"MOMENTUM SURGE: buy_score={buy_score}, rsi={m.rsi:.1f}, roc={m.roc:.2%}, vol={m.volume_ratio:.1f}x"
            return Signal.BUY
        
        if sell_score >= 6:
            self._signal_reason = f"MOMENTUM WEAKENING: sell_score={sell_score}, rsi={m.rsi:.1f}, roc={m.roc:.2%}"
            return Signal.SELL
        
        # Exit signals
        if buy_score >= 4 and self._last_signal == Signal.BUY:
            if m.rsi > 75:
                self._signal_reason = f"RSI overbought ({m.rsi:.1f}) - take profit"
                return Signal.SELL
        
        if sell_score >= 4 and self._last_signal == Signal.SELL:
            if m.rsi < 25:
                self._signal_reason = f"RSI oversold ({m.rsi:.1f}) - potential bottom"
                return Signal.BUY
        
        self._signal_reason = f"Neutral: buy={buy_score}, sell={sell_score}, rsi={m.rsi:.1f}"
        return Signal.NEUTRAL
    
    def get_momentum(self) -> Optional[MomentumData]:
        """Get current momentum data"""
        return self._current_momentum
    
    def get_signal(self) -> Tuple[Signal, str]:
        """Get current signal and reason"""
        return self._last_signal, self._signal_reason
    
    def get_statistics(self) -> Dict:
        """Get strategy statistics"""
        m = self._current_momentum
        
        return {
            "signal": self._last_signal.value,
            "reason": self._signal_reason,
            "rsi": m.rsi if m else 0,
            "momentum": m.momentum if m else 0,
            "roc": m.roc if m else 0,
            "volume_ratio": m.volume_ratio if m else 0,
            "trend_strength": m.trend_strength if m else 0,
        }
    
    def reset(self):
        """Reset strategy state"""
        self._prices.clear()
        self._volumes.clear()
        self._gains.clear()
        self._losses.clear()
        self._current_momentum = None
        self._last_signal = Signal.NEUTRAL
        logger.info("Momentum Strategy reset")


def create_momentum_strategy(
    momentum_period: int = 10,
    volume_threshold: float = 1.5
) -> MomentumSurgeStrategy:
    """Create Momentum Surge Strategy"""
    return MomentumSurgeStrategy(
        momentum_period=momentum_period,
        volume_threshold=volume_threshold
    )
