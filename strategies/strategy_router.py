"""
Strategy Router
AI-powered strategy selection based on market conditions
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    LOW_VOLATILITY = "LOW_VOLATILITY"


@dataclass
class StrategyScore:
    """Strategy scoring"""
    strategy_name: str
    signal: str
    confidence: float
    score: float


@dataclass
class RouterResult:
    """Router decision result"""
    selected_strategy: str
    regime: MarketRegime
    scores: List[StrategyScore]
    reason: str


class StrategyRouter:
    """
    Strategy Router - AI Strategy Selector
    
    Analyzes market conditions and selects the best strategy
    """
    
    def __init__(
        self,
        strategies: Dict = None
    ):
        """
        Initialize Strategy Router
        
        Args:
            strategies: Dict of strategy_name -> strategy_instance
        """
        self.strategies = strategies or {}
        
        self._regime: MarketRegime = MarketRegime.RANGING
        self._last_result: Optional[RouterResult] = None
        
        # Regime indicators
        self._price_history: List[float] = []
        self._volume_history: List[float] = []
        self._volatility_history: List[float] = []
        
        # Strategy weights for different regimes
        self._regime_strategies = {
            MarketRegime.TRENDING_UP: ["momentum", "ma_crossover"],
            MarketRegime.TRENDING_DOWN: ["momentum", "rsi_divergence"],
            MarketRegime.RANGING: ["mean_reversion", "rsi_divergence", "bollinger"],
            MarketRegime.VOLATILE: ["mean_reversion", "rsi_divergence"],
            MarketRegime.LOW_VOLATILITY: ["momentum", "bollinger"],
        }
        
        logger.info(f"Strategy Router initialized with {len(self.strategies)} strategies")
    
    def register_strategy(self, name: str, strategy):
        """Register a strategy"""
        self.strategies[name] = strategy
        logger.info(f"Registered strategy: {name}")
    
    def update(self, price: float, volume: float = 0) -> RouterResult:
        """
        Update with new data and get best strategy
        
        Args:
            price: Current price
            volume: Current volume
        
        Returns:
            RouterResult
        """
        self._price_history.append(price)
        self._volume_history.append(volume)
        
        # Detect market regime
        regime = self._detect_regime(price)
        self._regime = regime
        
        # Score each strategy
        scores = self._score_strategies(price, volume)
        
        # Select best strategy
        if scores:
            best = max(scores, key=lambda s: s.score)
            selected = best.strategy_name
            reason = f"Regime: {regime.value}, Score: {best.score:.2f}, Signal: {best.signal}"
        else:
            selected = "neutral"
            reason = "No strategy scores available"
            scores = []
        
        self._last_result = RouterResult(
            selected_strategy=selected,
            regime=regime,
            scores=scores,
            reason=reason
        )
        
        logger.debug(f"Router: {selected} selected (regime: {regime.value})")
        
        return self._last_result
    
    def _detect_regime(self, price: float) -> MarketRegime:
        """Detect current market regime"""
        
        if len(self._price_history) < 20:
            return MarketRegime.RANGING
        
        prices = self._price_history[-20:]
        
        # Calculate trend (simple linear regression slope)
        n = len(prices)
        x_mean = (n - 1) / 2
        y_mean = sum(prices) / n
        
        numerator = sum((i - x_mean) * (prices[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Normalize slope to percentage
        avg_price = sum(prices) / n
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        # Calculate volatility
        variance = sum((p - avg_price) ** 2 for p in prices) / n
        std = variance ** 0.5
        volatility = (std / avg_price) * 100 if avg_price > 0 else 0
        
        # Determine regime
        if volatility > 3.0:
            return MarketRegime.VOLATILE
        elif volatility < 0.5:
            return MarketRegime.LOW_VOLATILITY
        elif slope_pct > 0.5:
            return MarketRegime.TRENDING_UP
        elif slope_pct < -0.5:
            return MarketRegime.TRENDING_DOWN
        else:
            return MarketRegime.RANGING
    
    def _score_strategies(self, price: float, volume: float) -> List[StrategyScore]:
        """Score all strategies"""
        scores = []
        
        for name, strategy in self.strategies.items():
            try:
                # Get signal from strategy
                if hasattr(strategy, 'update'):
                    signal = strategy.update(price, volume)
                    signal_str = signal.value if hasattr(signal, 'value') else str(signal)
                elif hasattr(strategy, 'get_signal'):
                    signal_obj, _ = strategy.get_signal()
                    signal_str = signal_obj.value if hasattr(signal_obj, 'value') else str(signal_obj)
                else:
                    continue
                
                # Calculate confidence score
                confidence = self._calculate_confidence(name, signal_str)
                score = confidence
                
                # Boost score for regime-appropriate strategies
                if name in self._regime_strategies.get(self._regime, []):
                    score *= 1.2
                
                scores.append(StrategyScore(
                    strategy_name=name,
                    signal=signal_str,
                    confidence=confidence,
                    score=score
                ))
                
            except Exception as e:
                logger.warning(f"Error scoring strategy {name}: {e}")
        
        # Sort by score
        scores.sort(key=lambda s: s.score, reverse=True)
        
        return scores
    
    def _calculate_confidence(self, strategy_name: str, signal: str) -> float:
        """Calculate confidence score for strategy signal"""
        
        # Base confidence
        if signal == "NEUTRAL":
            return 0.3
        
        # Strategy-specific confidence
        confidence_map = {
            "momentum": 0.75,
            "rsi_divergence": 0.70,
            "bollinger": 0.70,
            "mean_reversion": 0.65,
            "ma_crossover": 0.60,
        }
        
        base = confidence_map.get(strategy_name, 0.5)
        
        # Boost for strong signals
        if signal in ["BUY", "SELL"]:
            base += 0.1
        
        return min(1.0, base)
    
    def get_regime(self) -> MarketRegime:
        """Get current market regime"""
        return self._regime
    
    def get_best_strategy(self) -> str:
        """Get best strategy name"""
        if self._last_result:
            return self._last_result.selected_strategy
        return "neutral"
    
    def get_all_scores(self) -> List[StrategyScore]:
        """Get all strategy scores"""
        if self._last_result:
            return self._last_result.scores
        return []
    
    def get_statistics(self) -> Dict:
        """Get router statistics"""
        return {
            "current_regime": self._regime.value,
            "selected_strategy": self.get_best_strategy(),
            "strategies_count": len(self.strategies),
            "scores": [
                {"name": s.strategy_name, "signal": s.signal, "score": s.score}
                for s in self.get_all_scores()
            ] if self.get_all_scores() else [],
        }
    
    def reset(self):
        """Reset router state"""
        self._price_history.clear()
        self._volume_history.clear()
        self._volatility_history.clear()
        self._regime = MarketRegime.RANGING
        logger.info("Strategy Router reset")


def create_strategy_router() -> StrategyRouter:
    """Create Strategy Router"""
    return StrategyRouter()
