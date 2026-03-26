"""
Trailing Stop Manager
Dynamic trailing stops that lock in profits as price moves in your favor
"""
import time
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class TrailingStopType(Enum):
    PERCENT = "percent"  # Percentage-based trailing stop
    PRICE = "price"  # Price-based trailing stop
    ATR = "atr"  # ATR-based trailing stop


@dataclass
class TrailingStopOrder:
    """Trailing stop order data"""
    order_id: str
    symbol: str
    side: str  # LONG or SHORT
    quantity: float
    activation_price: float  # Price at which trailing stop activates
    callback_rate: float  # Trailing stop percentage
    stop_price: float  # Current trailing stop price
    is_active: bool = False
    triggered: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    triggered_at: Optional[float] = None


class TrailingStop:
    """
    Trailing Stop Manager
    Manages dynamic trailing stops for positions
    """
    
    def __init__(
        self,
        default_callback_rate: float = 0.5,  # 0.5% default
        min_activation_percent: float = 1.0,  # 1% profit before activation
        price_precision: int = 2
    ):
        """
        Initialize Trailing Stop Manager
        
        Args:
            default_callback_rate: Default trailing stop percentage
            min_activation_percent: Minimum profit % before activation
            price_precision: Price decimal places
        """
        self.default_callback_rate = default_callback_rate
        self.min_activation_percent = min_activation_percent
        self.price_precision = price_precision
        
        self._trailing_stops: Dict[str, TrailingStopOrder] = {}
        self._triggered_stops: List[TrailingStopOrder] = []
        
        logger.info(f"Trailing Stop initialized: callback={default_callback_rate}%, "
                   f"min_activation={min_activation_percent}%")
    
    def create_trailing_stop(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        callback_rate: float = None,
        activation_percent: float = None
    ) -> TrailingStopOrder:
        """
        Create a trailing stop for a position
        
        Args:
            order_id: Order/position ID
            symbol: Trading symbol
            side: LONG or SHORT
            quantity: Position quantity
            entry_price: Entry price
            callback_rate: Trailing stop percentage (None = use default)
            activation_percent: Profit % to activate trailing stop
        
        Returns:
            TrailingStopOrder
        """
        if callback_rate is None:
            callback_rate = self.default_callback_rate
        if activation_percent is None:
            activation_percent = self.min_activation_percent
        
        # Calculate activation price
        if side.upper() == "LONG":
            activation_price = entry_price * (1 + activation_percent / 100)
            # Initial stop price (below entry)
            stop_price = entry_price * (1 - callback_rate / 100)
        else:  # SHORT
            activation_price = entry_price * (1 - activation_percent / 100)
            # Initial stop price (above entry)
            stop_price = entry_price * (1 + callback_rate / 100)
        
        trailing_stop = TrailingStopOrder(
            order_id=order_id,
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            activation_price=activation_price,
            callback_rate=callback_rate,
            stop_price=stop_price
        )
        
        self._trailing_stops[order_id] = trailing_stop
        
        logger.info(f"Trailing stop created: {symbol} {side} {quantity} "
                   f"entry=${entry_price:.2f} stop=${stop_price:.2f} "
                   f"callback={callback_rate}%")
        
        return trailing_stop
    
    def update_trailing_stop(
        self,
        order_id: str,
        current_price: float
    ) -> Optional[float]:
        """
        Update trailing stop with current price
        
        Args:
            order_id: Order/position ID
            current_price: Current market price
        
        Returns:
            New stop price if updated, None otherwise
        """
        if order_id not in self._trailing_stops:
            return None
        
        ts = self._trailing_stops[order_id]
        
        # Check if activation price reached
        if not ts.is_active:
            if ts.side == "LONG" and current_price >= ts.activation_price:
                ts.is_active = True
                logger.info(f"Trailing stop activated: {order_id} "
                           f"(price: ${current_price:.2f})")
            elif ts.side == "SHORT" and current_price <= ts.activation_price:
                ts.is_active = True
                logger.info(f"Trailing stop activated: {order_id} "
                           f"(price: ${current_price:.2f})")
        
        if not ts.is_active:
            return ts.stop_price
        
        # Update stop price based on current price
        old_stop = ts.stop_price
        
        if ts.side == "LONG":
            # For long positions, trailing stop moves UP as price rises
            new_stop = current_price * (1 - ts.callback_rate / 100)
            if new_stop > ts.stop_price:
                ts.stop_price = new_stop
        else:  # SHORT
            # For short positions, trailing stop moves DOWN as price falls
            new_stop = current_price * (1 + ts.callback_rate / 100)
            if new_stop < ts.stop_price:
                ts.stop_price = new_stop
        
        # Check if trailing stop triggered
        if ts.side == "LONG" and current_price <= ts.stop_price:
            ts.triggered = True
            ts.triggered_at = time.time()
            self._triggered_stops.append(ts)
            del self._trailing_stops[order_id]
            logger.warning(f"TRAILING STOP TRIGGERED: {order_id} "
                          f"long @ ${current_price:.2f} (stop: ${ts.stop_price:.2f})")
            return ts.stop_price
        elif ts.side == "SHORT" and current_price >= ts.stop_price:
            ts.triggered = True
            ts.triggered_at = time.time()
            self._triggered_stops.append(ts)
            del self._trailing_stops[order_id]
            logger.warning(f"TRAILING STOP TRIGGERED: {order_id} "
                          f"short @ ${current_price:.2f} (stop: ${ts.stop_price:.2f})")
            return ts.stop_price
        
        if ts.stop_price != old_stop:
            ts.updated_at = time.time()
            logger.debug(f"Trailing stop updated: {order_id} "
                        f"${old_stop:.2f} -> ${ts.stop_price:.2f}")
        
        return ts.stop_price
    
    def cancel_trailing_stop(self, order_id: str) -> bool:
        """Cancel trailing stop"""
        if order_id in self._trailing_stops:
            del self._trailing_stops[order_id]
            logger.info(f"Trailing stop cancelled: {order_id}")
            return True
        return False
    
    def get_trailing_stop(self, order_id: str) -> Optional[TrailingStopOrder]:
        """Get trailing stop order"""
        return self._trailing_stops.get(order_id)
    
    def get_active_trailing_stops(self) -> List[TrailingStopOrder]:
        """Get all active trailing stops"""
        return list(self._trailing_stops.values())
    
    def get_triggered_stops(self) -> List[TrailingStopOrder]:
        """Get triggered trailing stops"""
        return self._triggered_stops
    
    def get_pending_stops(self) -> List[TrailingStopOrder]:
        """Get pending (not yet activated) trailing stops"""
        return [ts for ts in self._trailing_stops.values() if not ts.is_active]
    
    def should_trigger(self, order_id: str, current_price: float) -> bool:
        """Check if trailing stop should trigger"""
        if order_id not in self._trailing_stops:
            return False
        
        ts = self._trailing_stops[order_id]
        
        if ts.side == "LONG":
            return current_price <= ts.stop_price
        else:
            return current_price >= ts.stop_price
    
    def get_stop_distance_percent(self, order_id: str, current_price: float) -> float:
        """Get distance to stop as percentage"""
        if order_id not in self._trailing_stops:
            return 0.0
        
        ts = self._trailing_stops[order_id]
        
        if ts.side == "LONG":
            return (current_price - ts.stop_price) / current_price * 100
        else:
            return (ts.stop_price - current_price) / current_price * 100
    
    def get_statistics(self) -> Dict:
        """Get trailing stop statistics"""
        active = self.get_active_trailing_stops()
        pending = self.get_pending_stops()
        triggered = self.get_triggered_stops()
        
        return {
            "active_count": len(active),
            "pending_count": len(pending),
            "triggered_count": len(triggered),
            "default_callback_rate": self.default_callback_rate,
            "min_activation_percent": self.min_activation_percent,
        }
    
    def update_all_stops(self, prices: Dict[str, float]) -> Dict[str, float]:
        """
        Update all trailing stops with current prices
        
        Args:
            prices: Dict of symbol -> current price
        
        Returns:
            Dict of triggered order IDs
        """
        triggered = {}
        
        for order_id, ts in list(self._trailing_stops.items()):
            if ts.symbol in prices:
                current_price = prices[ts.symbol]
                
                # Check activation
                if not ts.is_active:
                    if (ts.side == "LONG" and current_price >= ts.activation_price) or \
                       (ts.side == "SHORT" and current_price <= ts.activation_price):
                        ts.is_active = True
                        logger.info(f"Trailing stop activated: {order_id}")
                
                # Check trigger
                if ts.is_active and self.should_trigger(order_id, current_price):
                    triggered[order_id] = current_price
                    ts.triggered = True
                    ts.triggered_at = time.time()
                    self._triggered_stops.append(ts)
                    del self._trailing_stops[order_id]
                    logger.warning(f"TRAILING STOP TRIGGERED: {order_id}")
                else:
                    # Update stop price
                    self.update_trailing_stop(order_id, current_price)
        
        return triggered
    
    def close_position(self, order_id: str) -> bool:
        """Close position and remove trailing stop"""
        return self.cancel_trailing_stop(order_id)


def create_trailing_stop(
    callback_rate: float = 0.5,
    min_activation: float = 1.0
) -> TrailingStop:
    """Create trailing stop manager"""
    return TrailingStop(callback_rate, min_activation)
