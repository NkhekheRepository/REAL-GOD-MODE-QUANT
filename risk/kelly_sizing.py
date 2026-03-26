"""
Kelly Criterion Position Sizing
Optimal position sizing based on win rate and payoff ratio
"""
import math
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KellyResult:
    """Kelly calculation result"""
    kelly_fraction: float  # Optimal fraction of bankroll
    optimal_fraction: float  # Conservative fraction (half-Kelly)
    min_fraction: float  # Minimum safe fraction
    recommended_position: float  # Recommended position value
    expected_growth_rate: float  # Expected logarithmic growth rate
    edge_description: str
    
    def to_dict(self) -> Dict:
        return {
            "kelly_fraction": self.kelly_fraction,
            "optimal_fraction": self.optimal_fraction,
            "min_fraction": self.min_fraction,
            "recommended_position": self.recommended_position,
            "expected_growth_rate": self.expected_growth_rate,
            "edge_description": self.edge_description,
        }


def calculate_kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction_cap: float = 0.25
) -> Tuple[float, str]:
    """
    Calculate Kelly Criterion fraction
    
    Formula: K% = W - (1-W)/R
    Where:
        W = Win rate (probability of winning)
        R = Win/Loss ratio (average win / average loss)
    
    Args:
        win_rate: Win probability (0.0 to 1.0)
        avg_win: Average win amount
        avg_loss: Average loss amount
        fraction_cap: Maximum allowed Kelly fraction (default 25%)
    
    Returns:
        Tuple of (kelly_fraction, description)
    """
    if avg_loss == 0:
        logger.warning("Average loss is zero, cannot calculate Kelly")
        return 0.0, "Invalid (avg_loss=0)"
    
    # Calculate win/loss ratio
    win_loss_ratio = avg_win / avg_loss
    
    # Calculate raw Kelly
    kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
    
    # Cap the Kelly fraction
    kelly = min(kelly, fraction_cap)
    kelly = max(kelly, 0)  # Never negative
    
    # Determine edge description
    if kelly >= 0.20:
        edge = "STRONG"
    elif kelly >= 0.10:
        edge = "MODERATE"
    elif kelly >= 0.05:
        edge = "WEAK"
    else:
        edge = "NO EDGE"
    
    logger.info(f"Kelly: {kelly:.2%}, Win Rate: {win_rate:.1%}, Win/Loss: {win_loss_ratio:.2f}")
    
    return kelly, edge


def calculate_kelly_from_trades(
    trades: list,
    fraction_cap: float = 0.25
) -> KellyResult:
    """
    Calculate Kelly from historical trade data
    
    Args:
        trades: List of trade PnL values
        fraction_cap: Maximum Kelly fraction
    
    Returns:
        KellyResult
    """
    if not trades or len(trades) < 10:
        return KellyResult(
            kelly_fraction=0.0,
            optimal_fraction=0.0,
            min_fraction=0.0,
            recommended_position=0.0,
            expected_growth_rate=0.0,
            edge_description="INSUFFICIENT DATA"
        )
    
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    
    win_rate = len(wins) / len(trades)
    
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0
    
    if avg_loss == 0:
        return KellyResult(
            kelly_fraction=0.0,
            optimal_fraction=0.0,
            min_fraction=0.0,
            recommended_position=0.0,
            expected_growth_rate=0.0,
            edge_description="NO LOSSES"
        )
    
    kelly, edge = calculate_kelly_fraction(win_rate, avg_win, avg_loss, fraction_cap)
    
    # Half-Kelly (more conservative)
    optimal = kelly / 2
    
    # Minimum safe fraction (quarter-Kelly)
    min_fraction = kelly / 4
    
    # Win/loss ratio for expected growth
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    # Expected growth rate (logarithmic)
    if kelly > 0 and win_rate > 0 and win_loss_ratio > 0:
        expected_growth = win_rate * math.log(1 + kelly * win_loss_ratio) + \
                         (1 - win_rate) * math.log(1 - kelly)
    else:
        expected_growth = 0
    
    return KellyResult(
        kelly_fraction=kelly,
        optimal_fraction=optimal,
        min_fraction=min_fraction,
        recommended_position=0.0,  # Will be calculated with portfolio value
        expected_growth_rate=expected_growth,
        edge_description=edge
    )


class KellySizer:
    """
    Kelly Criterion Position Sizer
    """
    
    def __init__(
        self,
        portfolio_value: float,
        fraction_cap: float = 0.25,
        use_fraction: str = "optimal"  # "full", "optimal", "min"
    ):
        """
        Initialize Kelly Sizer
        
        Args:
            portfolio_value: Total portfolio value
            fraction_cap: Maximum Kelly fraction (default 25%)
            use_fraction: Which fraction to use ("full", "optimal", "min")
        """
        self.portfolio_value = portfolio_value
        self.fraction_cap = fraction_cap
        self.use_fraction = use_fraction
        
        self._trades: list = []
        self._last_kelly: Optional[KellyResult] = None
        
        logger.info(f"Kelly Sizer initialized: ${portfolio_value:.2f}, cap: {fraction_cap:.0%}")
    
    def add_trade(self, pnl: float):
        """Add trade result for tracking"""
        self._trades.append(pnl)
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        win_rate: float = None,
        avg_win: float = None,
        avg_loss: float = None
    ) -> float:
        """
        Calculate position size using Kelly Criterion
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            win_rate: Optional win rate (if None, calculated from trades)
            avg_win: Optional average win (if None, calculated from trades)
            avg_loss: Optional average loss (if None, calculated from trades)
        
        Returns:
            Position size (quantity)
        """
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            logger.warning("Stop loss too close to entry")
            return 0.0
        
        # Calculate Kelly from provided values or historical data
        if win_rate is not None and avg_win is not None and avg_loss is not None:
            kelly, edge = calculate_kelly_fraction(win_rate, avg_win, avg_loss, self.fraction_cap)
        else:
            kelly_result = calculate_kelly_from_trades(self._trades, self.fraction_cap)
            kelly = kelly_result.kelly_fraction
            self._last_kelly = kelly_result
        
        # Select fraction based on settings
        if self.use_fraction == "full":
            fraction = kelly
        elif self.use_fraction == "optimal":
            fraction = kelly / 2
        else:  # min
            fraction = kelly / 4
        
        # Calculate position value
        position_value = self.portfolio_value * fraction
        
        # Calculate quantity
        quantity = position_value / entry_price
        
        logger.info(f"Kelly position: {quantity:.4f} @ ${entry_price:.2f} "
                   f"(fraction: {fraction:.2%}, value: ${position_value:.2f})")
        
        return quantity
    
    def calculate_position_value(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_percent: float = 1.0,
        use_kelly: bool = True
    ) -> float:
        """
        Calculate position value (not quantity)
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_percent: Risk as percentage of portfolio
            use_kelly: Use Kelly criterion instead of fixed risk
    
    Returns:
            Position value in dollars
        """
        if use_kelly and self._trades:
            kelly_result = calculate_kelly_from_trades(self._trades, self.fraction_cap)
            
            if self.use_fraction == "full":
                fraction = kelly_result.kelly_fraction
            elif self.use_fraction == "optimal":
                fraction = kelly_result.optimal_fraction
            else:
                fraction = kelly_result.min_fraction
            
            return self.portfolio_value * fraction
        else:
            risk_amount = self.portfolio_value * (risk_percent / 100)
            return risk_amount / abs(entry_price - stop_loss_price) * entry_price
    
    def update_portfolio_value(self, value: float):
        """Update portfolio value"""
        self.portfolio_value = value
        logger.debug(f"Portfolio value updated: ${value:.2f}")
    
    def get_statistics(self) -> Dict:
        """Get Kelly statistics"""
        if not self._trades:
            return {
                "trades_count": 0,
                "kelly_fraction": 0.0,
                "edge": "NO DATA"
            }
        
        kelly_result = calculate_kelly_from_trades(self._trades, self.fraction_cap)
        
        wins = [t for t in self._trades if t > 0]
        losses = [t for t in self._trades if t < 0]
        
        return {
            "trades_count": len(self._trades),
            "wins_count": len(wins),
            "losses_count": len(losses),
            "win_rate": len(wins) / len(self._trades),
            "kelly_fraction": kelly_result.kelly_fraction,
            "optimal_fraction": kelly_result.optimal_fraction,
            "expected_growth": kelly_result.expected_growth_rate,
            "edge": kelly_result.edge_description,
        }
    
    def get_recommended_leverage(self, min_leverage: int = 1, max_leverage: int = 75) -> int:
        """Get recommended leverage based on Kelly"""
        if not self._trades:
            return min_leverage
        
        kelly_result = calculate_kelly_from_trades(self._trades, self.fraction_cap)
        
        if kelly_result.edge_description == "STRONG":
            return max_leverage
        elif kelly_result.edge_description == "MODERATE":
            return min(50, max_leverage)
        elif kelly_result.edge_description == "WEAK":
            return min(20, max_leverage)
        else:
            return min_leverage
