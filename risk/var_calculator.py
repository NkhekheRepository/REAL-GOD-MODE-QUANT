"""
Value at Risk (VaR) Calculator
Real-time portfolio risk calculation
"""
import time
import math
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import deque
import random

logger = logging.getLogger(__name__)


class VaRMethod(Enum):
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"


@dataclass
class VaRResult:
    """VaR calculation result"""
    var_95: float  # VaR at 95% confidence
    var_99: float  # VaR at 99% confidence
    cvar_95: float  # CVaR (Expected Shortfall) at 95%
    cvar_99: float  # CVaR at 99%
    max_drawdown: float  # Historical max drawdown
    volatility: float  # Portfolio volatility
    confidence: str  # Risk level description


class VaRCalculator:
    """
    Value at Risk Calculator
    
    Calculates portfolio risk using multiple methods:
    - Historical: Based on actual returns
    - Parametric: Normal distribution assumption
    - Monte Carlo: Random simulation
    """
    
    def __init__(
        self,
        method: VaRMethod = VaRMethod.HISTORICAL,
        confidence_levels: List[float] = None,
        lookback_period: int = 100
    ):
        """
        Initialize VaR Calculator
        
        Args:
            method: VaR calculation method
            confidence_levels: List of confidence levels (e.g., [0.95, 0.99])
            lookback_period: Number of periods for calculation
        """
        self.method = method
        self.confidence_levels = confidence_levels or [0.95, 0.99]
        self.lookback_period = lookback_period
        
        self._returns: deque = deque(maxlen=lookback_period)
        self._portfolio_values: deque = deque(maxlen=lookback_period)
        self._price_history: Dict[str, deque] = {}
        
        self._last_var: Optional[VaRResult] = None
        
        logger.info(f"VaR Calculator initialized: method={method.value}, "
                   f"lookback={lookback_period}")
    
    def add_return(self, portfolio_return: float):
        """Add portfolio return for calculation"""
        self._returns.append(portfolio_return)
    
    def add_price(self, symbol: str, price: float):
        """Add price for position"""
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=self.lookback_period)
        self._price_history[symbol].append(price)
    
    def add_position_return(
        self,
        symbol: str,
        position_value: float,
        entry_price: float,
        current_price: float
    ):
        """Add position return"""
        if entry_price <= 0:
            return
        
        position_return = (current_price - entry_price) / entry_price
        
        # Weight by position value
        weighted_return = position_return * position_value
        
        self._returns.append(weighted_return)
        
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=self.lookback_period)
        self._price_history[symbol].append(current_price)
    
    def calculate_historical_var(
        self,
        portfolio_value: float,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Historical VaR
        
        Args:
            portfolio_value: Current portfolio value
            confidence: Confidence level (e.g., 0.95 for 95%)
        
        Returns:
            VaR as dollar amount
        """
        if len(self._returns) < 10:
            # Not enough data, use placeholder
            return portfolio_value * 0.02  # 2% placeholder
        
        # Sort returns
        sorted_returns = sorted(self._returns)
        
        # Find the percentile
        index = int((1 - confidence) * len(sorted_returns))
        var_return = sorted_returns[index]
        
        # VaR in dollars
        var_dollars = abs(var_return) * portfolio_value
        
        return var_dollars
    
    def calculate_parametric_var(
        self,
        portfolio_value: float,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Parametric VaR (Normal distribution)
        
        Args:
            portfolio_value: Current portfolio value
            confidence: Confidence level
        
        Returns:
            VaR as dollar amount
        """
        if len(self._returns) < 10:
            return portfolio_value * 0.02
        
        # Calculate mean and std dev
        mean_return = sum(self._returns) / len(self._returns)
        variance = sum((r - mean_return) ** 2 for r in self._returns) / len(self._returns)
        std_dev = math.sqrt(variance)
        
        # Z-score for confidence level
        try:
            from scipy import stats
            z_score = stats.norm.ppf(1 - confidence)
        except ImportError:
            # Fallback: approximate Z-scores
            z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
            z_score = z_scores.get(confidence, 1.645)
        
        # VaR = portfolio * (mean - z * std)
        var_return = mean_return - z_score * std_dev
        
        # VaR in dollars (positive value)
        var_dollars = abs(var_return) * portfolio_value
        
        return var_dollars
    
    def calculate_monte_carlo_var(
        self,
        portfolio_value: float,
        confidence: float = 0.95,
        simulations: int = 10000
    ) -> float:
        """
        Calculate Monte Carlo VaR
        
        Args:
            portfolio_value: Current portfolio value
            confidence: Confidence level
            simulations: Number of simulations
        
        Returns:
            VaR as dollar amount
        """
        if len(self._returns) < 10:
            return portfolio_value * 0.02
        
        # Calculate mean and std
        mean_return = sum(self._returns) / len(self._returns)
        variance = sum((r - mean_return) ** 2 for r in self._returns) / len(self._returns)
        std_dev = math.sqrt(variance)
        
        # Simulate returns
        simulated_returns = [
            random.gauss(mean_return, std_dev)
            for _ in range(simulations)
        ]
        
        # Sort and find VaR
        sorted_returns = sorted(simulated_returns)
        index = int((1 - confidence) * simulations)
        var_return = sorted_returns[index]
        
        return abs(var_return) * portfolio_value
    
    def calculate_var(
        self,
        portfolio_value: float,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate VaR using configured method
        
        Args:
            portfolio_value: Current portfolio value
            confidence: Confidence level
        
        Returns:
            VaR as dollar amount
        """
        if self.method == VaRMethod.PARAMETRIC:
            return self.calculate_parametric_var(portfolio_value, confidence)
        elif self.method == VaRMethod.MONTE_CARLO:
            return self.calculate_monte_carlo_var(portfolio_value, confidence)
        else:
            return self.calculate_historical_var(portfolio_value, confidence)
    
    def calculate_cvar(
        self,
        portfolio_value: float,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate CVaR (Expected Shortfall)
        
        CVaR is the expected loss given that the loss exceeds VaR
        
        Args:
            portfolio_value: Current portfolio value
            confidence: Confidence level
        
        Returns:
            CVaR as dollar amount
        """
        if len(self._returns) < 10:
            return portfolio_value * 0.03
        
        var = self.calculate_var(portfolio_value, confidence)
        var_percent = var / portfolio_value
        
        # CVaR = average of returns worse than VaR
        cutoff = -var_percent
        tail_returns = [r for r in self._returns if r <= cutoff]
        
        if tail_returns:
            cvar_percent = abs(sum(tail_returns) / len(tail_returns))
            return cvar_percent * portfolio_value
        
        return var * 1.5  # Fallback
    
    def calculate_full_var(self, portfolio_value: float) -> VaRResult:
        """
        Calculate full VaR report
        
        Args:
            portfolio_value: Current portfolio value
        
        Returns:
            VaRResult
        """
        # Calculate for different confidence levels
        var_95 = self.calculate_var(portfolio_value, 0.95)
        var_99 = self.calculate_var(portfolio_value, 0.99)
        
        cvar_95 = self.calculate_cvar(portfolio_value, 0.95)
        cvar_99 = self.calculate_cvar(portfolio_value, 0.99)
        
        # Calculate volatility
        if len(self._returns) >= 2:
            mean_return = sum(self._returns) / len(self._returns)
            variance = sum((r - mean_return) ** 2 for r in self._returns) / len(self._returns)
            volatility = math.sqrt(variance) * math.sqrt(252) * 100  # Annualized %
        else:
            volatility = 0.0
        
        # Calculate max drawdown
        max_dd = self._calculate_max_drawdown()
        
        # Determine confidence description
        if var_95 / portfolio_value < 0.01:
            confidence = "LOW"
        elif var_95 / portfolio_value < 0.03:
            confidence = "MODERATE"
        elif var_95 / portfolio_value < 0.05:
            confidence = "HIGH"
        else:
            confidence = "CRITICAL"
        
        self._last_var = VaRResult(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_drawdown=max_dd,
            volatility=volatility,
            confidence=confidence
        )
        
        return self._last_var
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum historical drawdown"""
        if len(self._portfolio_values) < 2:
            return 0.0
        
        peak = self._portfolio_values[0]
        max_dd = 0.0
        
        for value in self._portfolio_values:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd * 100  # As percentage
    
    def add_portfolio_value(self, value: float):
        """Add portfolio value for drawdown calculation"""
        self._portfolio_values.append(value)
    
    def get_var_percent(self, portfolio_value: float, confidence: float = 0.95) -> float:
        """Get VaR as percentage"""
        var = self.calculate_var(portfolio_value, confidence)
        return (var / portfolio_value) * 100 if portfolio_value > 0 else 0
    
    def get_risk_level(self, portfolio_value: float) -> Tuple[str, str]:
        """
        Get current risk level
        
        Returns:
            Tuple of (level, description)
        """
        if self._last_var:
            var_percent = (self._last_var.var_95 / portfolio_value) * 100 if portfolio_value > 0 else 0
        else:
            var_percent = self.get_var_percent(portfolio_value, 0.95)
        
        if var_percent < 1.0:
            return "LOW", f"VaR: {var_percent:.2f}% - Safe to trade"
        elif var_percent < 2.5:
            return "MODERATE", f"VaR: {var_percent:.2f}% - Normal risk"
        elif var_percent < 5.0:
            return "HIGH", f"VaR: {var_percent:.2f}% - Consider reducing exposure"
        else:
            return "CRITICAL", f"VaR: {var_percent:.2f}% - Reduce positions immediately!"
    
    def get_statistics(self) -> Dict:
        """Get VaR statistics"""
        return {
            "method": self.method.value,
            "lookback_period": self.lookback_period,
            "sample_count": len(self._returns),
            "last_var_95": self._last_var.var_95 if self._last_var else 0,
            "last_var_99": self._last_var.var_99 if self._last_var else 0,
            "last_cvar_95": self._last_var.cvar_95 if self._last_var else 0,
            "volatility": self._last_var.volatility if self._last_var else 0,
            "confidence": self._last_var.confidence if self._last_var else "UNKNOWN",
        }
    
    def get_risk_report(self, portfolio_value: float) -> Dict:
        """Get comprehensive risk report"""
        var_result = self.calculate_full_var(portfolio_value)
        risk_level, risk_desc = self.get_risk_level(portfolio_value)
        
        return {
            "var_95_dollars": var_result.var_95,
            "var_95_percent": (var_result.var_95 / portfolio_value * 100) if portfolio_value > 0 else 0,
            "var_99_dollars": var_result.var_99,
            "var_99_percent": (var_result.var_99 / portfolio_value * 100) if portfolio_value > 0 else 0,
            "cvar_95": var_result.cvar_95,
            "cvar_99": var_result.cvar_99,
            "max_drawdown_percent": var_result.max_drawdown,
            "volatility_annualized": var_result.volatility,
            "risk_level": risk_level,
            "risk_description": risk_desc,
            "method": self.method.value,
        }


def create_var_calculator(
    method: str = "historical",
    lookback: int = 100
) -> VaRCalculator:
    """Create VaR calculator"""
    return VaRCalculator(
        method=VaRMethod[method.upper()],
        lookback_period=lookback
    )
