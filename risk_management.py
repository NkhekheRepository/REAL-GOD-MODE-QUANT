"""
Risk Management for vnpy-based God Mode Quant Trading Orchestrator
Implements position sizing, stop-loss, take-profit, portfolio risk limits, and risk metrics
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for positions and portfolio"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PositionRisk:
    """Risk metrics for a single position"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    risk_amount: float = 0.0  # Amount at risk if stop loss is hit
    risk_percent: float = 0.0  # Percent of portfolio at risk
    timestamp: float = field(default_factory=time.time)
    
    def update_metrics(self, current_price: float, portfolio_value: float):
        """Update position metrics based on current price"""
        self.current_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        self.unrealized_pnl_percent = (current_price - self.entry_price) / self.entry_price * 100
        
        # Calculate risk if stop loss is set
        if self.stop_loss is not None:
            self.risk_amount = abs(self.entry_price - self.stop_loss) * abs(self.quantity)
            self.risk_percent = (self.risk_amount / portfolio_value) * 100 if portfolio_value > 0 else 0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "risk_amount": self.risk_amount,
            "risk_percent": self.risk_percent,
            "timestamp": self.timestamp
        }


@dataclass
class PortfolioRisk:
    """Risk metrics for the entire portfolio"""
    total_value: float = 0.0
    cash: float = 0.0
    positions_value: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_unrealized_pnl_percent: float = 0.0
    total_risk_amount: float = 0.0
    total_risk_percent: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: Optional[float] = None
    var_95: float = 0.0  # Value at Risk (95% confidence)
    position_count: int = 0
    timestamp: float = field(default_factory=time.time)
    positions: Dict[str, PositionRisk] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "total_value": self.total_value,
            "cash": self.cash,
            "positions_value": self.positions_value,
            "total_unrealized_pnl": self.total_unrealized_pnl,
            "total_unrealized_pnl_percent": self.total_unrealized_pnl_percent,
            "total_risk_amount": self.total_risk_amount,
            "total_risk_percent": self.total_risk_percent,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "var_95": self.var_95,
            "position_count": self.position_count,
            "timestamp": self.timestamp,
            "positions": {k: v.to_dict() for k, v in self.positions.items()}
        }


class RiskManager:
    """Central risk management system for the trading orchestrator"""
    
    def __init__(self, 
                 max_portfolio_risk_percent: float = 2.0,
                 max_position_risk_percent: float = 0.5,
                 max_drawdown_percent: float = 10.0,
                 default_stop_loss_percent: float = 2.0,
                 default_take_profit_percent: float = 4.0):
        """
        Initialize risk manager
        
        Args:
            max_portfolio_risk_percent: Maximum portfolio risk as percentage
            max_position_risk_percent: Maximum risk per position as percentage
            max_drawdown_percent: Maximum allowed drawdown before triggering alerts
            default_stop_loss_percent: Default stop loss percentage from entry
            default_take_profit_percent: Default take profit percentage from entry
        """
        self.max_portfolio_risk_percent = max_portfolio_risk_percent
        self.max_position_risk_percent = max_position_risk_percent
        self.max_drawdown_percent = max_drawdown_percent
        self.default_stop_loss_percent = default_stop_loss_percent
        self.default_take_profit_percent = default_take_profit_percent
        
        # Portfolio tracking
        self.portfolio = PortfolioRisk()
        self.historical_values: List[Tuple[float, float]] = []  # (timestamp, value)
        self.peak_value = 0.0
        
    def calculate_position_size(self, 
                              signal_price: float,
                              stop_loss_price: float,
                              portfolio_value: float,
                              risk_percent: Optional[float] = None) -> float:
        """
        Calculate position size based on risk parameters
        
        Args:
            signal_price: Entry price for the position
            stop_loss_price: Stop loss price
            portfolio_value: Current portfolio value
            risk_percent: Percentage of portfolio to risk (uses default if None)
            
        Returns:
            Position size (quantity)
        """
        if risk_percent is None:
            risk_percent = self.max_position_risk_percent
        
        # Validate inputs
        if signal_price <= 0 or stop_loss_price <= 0 or portfolio_value <= 0:
            logger.warning("Invalid inputs for position size calculation")
            return 0.0
        
        # Calculate risk per share
        risk_per_share = abs(signal_price - stop_loss_price)
        if risk_per_share <= 0:
            logger.warning("Stop loss too close to entry price")
            return 0.0
        
        # Calculate dollar amount to risk
        risk_amount = portfolio_value * (risk_percent / 100)
        
        # Calculate position size
        position_size = risk_amount / risk_per_share
        
        logger.info(f"Calculated position size: {position_size:.4f} "
                   f"(risk: {risk_amount:.2f}, risk per share: {risk_per_share:.2f})")
        
        return position_size
    
    def add_position(self, 
                    symbol: str,
                    quantity: float,
                    entry_price: float,
                    stop_loss_percent: Optional[float] = None,
                    take_profit_percent: Optional[float] = None) -> bool:
        """
        Add a new position to the portfolio
        
        Args:
            symbol: Trading symbol
            quantity: Position quantity (positive for long, negative for short)
            entry_price: Entry price
            stop_loss_percent: Stop loss percentage from entry (uses default if None)
            take_profit_percent: Take profit percentage from entry (uses default if None)
            
        Returns:
            True if position was added successfully
        """
        try:
            # Use defaults if not specified
            if stop_loss_percent is None:
                stop_loss_percent = self.default_stop_loss_percent
            if take_profit_percent is None:
                take_profit_percent = self.default_take_profit_percent
            
            # Calculate stop loss and take profit prices
            if quantity > 0:  # Long position
                stop_loss = entry_price * (1 - stop_loss_percent / 100)
                take_profit = entry_price * (1 + take_profit_percent / 100)
            else:  # Short position
                stop_loss = entry_price * (1 + stop_loss_percent / 100)
                take_profit = entry_price * (1 - take_profit_percent / 100)
            
            # Create position risk object
            position = PositionRisk(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,  # Initially same as entry
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            # Add to portfolio
            self.portfolio.positions[symbol] = position
            self.portfolio.position_count = len(self.portfolio.positions)
            
            logger.info(f"Added position: {symbol} {quantity}@{entry_price:.2f} "
                       f"(SL: {stop_loss:.2f}, TP: {take_profit:.2f})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add position {symbol}: {e}")
            return False
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update the current price for a position and recalculate metrics"""
        if symbol not in self.portfolio.positions:
            logger.warning(f"Position {symbol} not found in portfolio")
            return False
        
        position = self.portfolio.positions[symbol]
        position.update_metrics(current_price, self.portfolio.total_value)
        return True
    
    def remove_position(self, symbol: str) -> bool:
        """Remove a position from the portfolio"""
        if symbol in self.portfolio.positions:
            del self.portfolio.positions[symbol]
            self.portfolio.position_count = len(self.portfolio.positions)
            logger.info(f"Removed position: {symbol}")
            return True
        else:
            logger.warning(f"Position {symbol} not found in portfolio")
            return False
    
    def update_portfolio_value(self, total_value: float, cash: float = None):
        """Update total portfolio value and recalculate risk metrics"""
        # Update historical tracking for drawdown calculation
        self.historical_values.append((time.time(), total_value))
        
        # Keep only last 1000 values to prevent memory issues
        if len(self.historical_values) > 1000:
            self.historical_values = self.historical_values[-1000:]
        
        # Update peak value for drawdown calculation
        if total_value > self.peak_value:
            self.peak_value = total_value
        
        # Calculate drawdown
        if self.peak_value > 0:
            drawdown = (self.peak_value - total_value) / self.peak_value * 100
            self.portfolio.max_drawdown = max(self.portfolio.max_drawdown, drawdown)
        
        # Update portfolio values
        old_total_value = self.portfolio.total_value
        self.portfolio.total_value = total_value
        if cash is not None:
            self.portfolio.cash = cash
        
        # Calculate positions value
        positions_value = sum(
            abs(pos.quantity * pos.current_price) 
            for pos in self.portfolio.positions.values()
        )
        self.portfolio.positions_value = positions_value
        
        # Calculate total P&L
        total_unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.portfolio.positions.values()
        )
        self.portfolio.total_unrealized_pnl = total_unrealized_pnl
        
        if self.portfolio.total_value > 0:
            self.portfolio.total_unrealized_pnl_percent = (
                total_unrealized_pnl / self.portfolio.total_value * 100
            )
        
        # Calculate total risk
        total_risk_amount = sum(
            pos.risk_amount for pos in self.portfolio.positions.values()
        )
        self.portfolio.total_risk_amount = total_risk_amount
        
        if self.portfolio.total_value > 0:
            self.portfolio.total_risk_percent = (
                total_risk_amount / self.portfolio.total_value * 100
            )
        
        # Check risk limits
        self._check_risk_limits()
        
        logger.debug(f"Updated portfolio value: {total_value:.2f}")
        return True
    
    def _check_risk_limits(self):
        """Check if any risk limits have been breached"""
        alerts = []
        
        # Check portfolio risk limit
        if self.portfolio.total_risk_percent > self.max_portfolio_risk_percent:
            alerts.append(
                f"Portfolio risk ({self.portfolio.total_risk_percent:.2f}%) "
                f"exceeds limit ({self.max_portfolio_risk_percent:.2f}%)"
            )
        
        # Check individual position risks
        for symbol, position in self.portfolio.positions.items():
            if position.risk_percent > self.max_position_risk_percent:
                alerts.append(
                    f"Position {symbol} risk ({position.risk_percent:.2f}%) "
                    f"exceeds limit ({self.max_position_risk_percent:.2f}%)"
                )
        
        # Check drawdown limit
        if self.portfolio.max_drawdown > self.max_drawdown_percent:
            alerts.append(
                f"Portfolio drawdown ({self.portfolio.max_drawdown:.2f}%) "
                f"exceeds limit ({self.max_drawdown_percent:.2f}%)"
            )
        
        # Log alerts
        for alert in alerts:
            logger.warning(f"RISK ALERT: {alert}")
        
        return alerts
    
    def should_stop_trading(self) -> Tuple[bool, List[str]]:
        """
        Determine if trading should be stopped based on risk limits
        
        Returns:
            Tuple of (should_stop, reasons)
        """
        reasons = []
        
        # Check portfolio risk limit
        if self.portfolio.total_risk_percent > self.max_portfolio_risk_percent:
            reasons.append(
                f"Portfolio risk ({self.portfolio.total_risk_percent:.2f}%) "
                f"exceeds limit ({self.max_portfolio_risk_percent:.2f}%)"
            )
        
        # Check individual position risks
        for symbol, position in self.portfolio.positions.items():
            if position.risk_percent > self.max_position_risk_percent:
                reasons.append(
                    f"Position {symbol} risk ({position.risk_percent:.2f}%) "
                    f"exceeds limit ({self.max_position_risk_percent:.2f}%)"
                )
        
        # Check drawdown limit
        if self.portfolio.max_drawdown > self.max_drawdown_percent:
            reasons.append(
                f"Portfolio drawdown ({self.portfolio.max_drawdown:.2f}%) "
                f"exceeds limit ({self.max_drawdown_percent:.2f}%)"
            )
        
        return len(reasons) > 0, reasons
    
    def get_risk_report(self) -> Dict:
        """Get comprehensive risk report"""
        should_stop, stop_reasons = self.should_stop_trading()
        
        return {
            "portfolio": self.portfolio.to_dict(),
            "risk_limits": {
                "max_portfolio_risk_percent": self.max_portfolio_risk_percent,
                "max_position_risk_percent": self.max_position_risk_percent,
                "max_drawdown_percent": self.max_drawdown_percent,
                "default_stop_loss_percent": self.default_stop_loss_percent,
                "default_take_profit_percent": self.default_take_profit_percent
            },
            "risk_status": {
                "should_stop_trading": should_stop,
                "stop_reasons": stop_reasons,
                "portfolio_risk_utilization": (
                    self.portfolio.total_risk_percent / self.max_portfolio_risk_percent * 100
                    if self.max_portfolio_risk_percent > 0 else 0
                )
            }
        }


# Global risk manager instance
risk_manager = RiskManager()


# Convenience functions
def calculate_position_size(signal_price: float, 
                          stop_loss_price: float,
                          portfolio_value: float,
                          risk_percent: Optional[float] = None) -> float:
    """Calculate position size based on risk parameters"""
    return risk_manager.calculate_position_size(
        signal_price, stop_loss_price, portfolio_value, risk_percent
    )


def add_position(symbol: str,
                quantity: float,
                entry_price: float,
                stop_loss_percent: Optional[float] = None,
                take_profit_percent: Optional[float] = None) -> bool:
    """Add a new position to the portfolio"""
    return risk_manager.add_position(
        symbol, quantity, entry_price, stop_loss_percent, take_profit_percent
    )


def update_position_price(symbol: str, current_price: float):
    """Update the current price for a position"""
    return risk_manager.update_position_price(symbol, current_price)


def remove_position(symbol: str) -> bool:
    """Remove a position from the portfolio"""
    return risk_manager.remove_position(symbol)


def update_portfolio_value(total_value: float, cash: float = None):
    """Update total portfolio value"""
    return risk_manager.update_portfolio_value(total_value, cash)


def get_risk_report() -> Dict:
    """Get comprehensive risk report"""
    return risk_manager.get_risk_report()


def should_stop_trading() -> Tuple[bool, List[str]]:
    """Determine if trading should be stopped based on risk limits"""
    return risk_manager.should_stop_trading()