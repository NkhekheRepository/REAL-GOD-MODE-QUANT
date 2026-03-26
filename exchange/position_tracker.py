"""
Position Tracker - Real-time position tracking and sync
"""
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Position data"""
    symbol: str
    position_side: str  # LONG, SHORT, BOTH
    quantity: float
    entry_price: float
    mark_price: float
    leverage: int
    unrealized_pnl: float
    realized_pnl: float = 0.0
    position_value: float = 0.0
    margin: float = 0.0
    isolated_margin: float = 0.0
    liquidation_price: float = 0.0
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "position_side": self.position_side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "mark_price": self.mark_price,
            "leverage": self.leverage,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "position_value": self.position_value,
            "margin": self.margin,
            "isolated_margin": self.isolated_margin,
            "liquidation_price": self.liquidation_price,
            "updated_at": datetime.fromtimestamp(self.updated_at).isoformat(),
        }
    
    @property
    def is_long(self) -> bool:
        return self.position_side == "LONG" or (self.position_side == "BOTH" and self.quantity > 0)
    
    @property
    def is_short(self) -> bool:
        return self.position_side == "SHORT" or (self.position_side == "BOTH" and self.quantity < 0)
    
    @property
    def pnl_percent(self) -> float:
        if self.position_value == 0:
            return 0.0
        return (self.unrealized_pnl / self.position_value) * 100
    
    @property
    def return_percent(self) -> float:
        cost = self.entry_price * abs(self.quantity)
        if cost == 0:
            return 0.0
        return (self.unrealized_pnl / cost) * 100


class PositionTracker:
    """
    Track positions in real-time with gateway sync
    """
    
    def __init__(self, gateway, update_interval: float = 1.0):
        self.gateway = gateway
        self.update_interval = update_interval
        
        self._positions: Dict[str, Position] = {}
        self._closed_positions: List[Position] = []
        self._position_history: List[Dict] = []
        
        self._total_pnl: float = 0.0
        self._total_realized_pnl: float = 0.0
        self._total_unrealized_pnl: float = 0.0
        
        self._last_sync: float = 0
        
        logger.info("Position Tracker initialized")
    
    def sync_positions(self) -> Dict[str, Position]:
        """Sync positions with exchange"""
        try:
            exchange_positions = self.gateway.get_positions()
            
            self._positions.clear()
            self._total_unrealized_pnl = 0.0
            
            for pos in exchange_positions:
                symbol = pos['symbol']
                
                position = Position(
                    symbol=symbol,
                    position_side=pos.get('positionSide', 'BOTH'),
                    quantity=pos['positionAmt'],
                    entry_price=pos['entryPrice'],
                    mark_price=pos['markPrice'],
                    leverage=pos['leverage'],
                    unrealized_pnl=pos['unrealizedProfit'],
                    position_value=abs(pos['positionAmt'] * pos['markPrice']),
                    margin=pos.get('positionInitialMargin', 0),
                    isolated_margin=pos.get('isolatedMargin', 0),
                )
                
                # Calculate liquidation price
                try:
                    position.liquidation_price = self.gateway.calculate_liquidation_price(
                        symbol,
                        position.position_side,
                        position.entry_price,
                        position.quantity,
                        position.leverage,
                        self.gateway.get_balance()
                    )
                except:
                    position.liquidation_price = 0
                
                self._positions[symbol] = position
                self._total_unrealized_pnl += position.unrealized_pnl
            
            self._last_sync = time.time()
            
            logger.info(f"Synced {len(self._positions)} positions, unrealized PnL: {self._total_unrealized_pnl:.2f}")
            
            return self._positions
            
        except Exception as e:
            logger.error(f"Failed to sync positions: {e}")
            return self._positions
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        if symbol in self._positions:
            return self._positions[symbol]
        
        self.sync_positions()
        return self._positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return self._positions
    
    def get_long_positions(self) -> List[Position]:
        """Get long positions"""
        return [p for p in self._positions.values() if p.is_long and p.quantity > 0]
    
    def get_short_positions(self) -> List[Position]:
        """Get short positions"""
        return [p for p in self._positions.values() if p.is_short and p.quantity < 0]
    
    def update_position(self, symbol: str, mark_price: float):
        """Update position with current mark price"""
        if symbol not in self._positions:
            return
        
        position = self._positions[symbol]
        position.mark_price = mark_price
        position.unrealized_pnl = (mark_price - position.entry_price) * position.quantity
        position.position_value = abs(position.quantity * mark_price)
        position.updated_at = time.time()
    
    def close_position(self, symbol: str, realized_pnl: float = 0.0) -> bool:
        """Mark position as closed"""
        if symbol not in self._positions:
            logger.warning(f"Position {symbol} not found")
            return False
        
        position = self._positions[symbol]
        
        self._closed_positions.append(position)
        
        self._position_history.append({
            'symbol': position.symbol,
            'side': position.position_side,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'exit_price': position.mark_price,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': position.unrealized_pnl,
            'closed_at': time.time(),
        })
        
        self._total_realized_pnl += realized_pnl
        self._total_pnl += realized_pnl
        
        del self._positions[symbol]
        
        logger.info(f"Position closed: {symbol} PnL: {realized_pnl:.2f}")
        
        return True
    
    def get_total_pnl(self) -> float:
        """Get total PnL"""
        return self._total_pnl
    
    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized PnL"""
        return self._total_unrealized_pnl
    
    def get_total_realized_pnl(self) -> float:
        """Get total realized PnL"""
        return self._total_realized_pnl
    
    def get_total_position_value(self) -> float:
        """Get total position value"""
        return sum(p.position_value for p in self._positions.values())
    
    def get_total_margin(self) -> float:
        """Get total margin used"""
        return sum(p.margin for p in self._positions.values())
    
    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self._positions)
    
    def get_positions_near_liquidation(self, buffer_percent: float = 10.0) -> List[Position]:
        """Get positions within X% of liquidation"""
        near_liquidation = []
        
        for position in self._positions.values():
            if position.liquidation_price <= 0:
                continue
            
            if position.is_long:
                distance = (position.mark_price - position.liquidation_price) / position.mark_price * 100
            else:
                distance = (position.liquidation_price - position.mark_price) / position.mark_price * 100
            
            if distance <= buffer_percent:
                near_liquidation.append(position)
        
        return near_liquidation
    
    def get_profitable_positions(self) -> List[Position]:
        """Get profitable positions"""
        return [p for p in self._positions.values() if p.unrealized_pnl > 0]
    
    def get_losing_positions(self) -> List[Position]:
        """Get losing positions"""
        return [p for p in self._positions.values() if p.unrealized_pnl < 0]
    
    def get_statistics(self) -> Dict:
        """Get position statistics"""
        return {
            "position_count": len(self._positions),
            "long_positions": len(self.get_long_positions()),
            "short_positions": len(self.get_short_positions()),
            "total_position_value": self.get_total_position_value(),
            "total_margin": self.get_total_margin(),
            "total_unrealized_pnl": self._total_unrealized_pnl,
            "total_realized_pnl": self._total_realized_pnl,
            "total_pnl": self._total_pnl,
            "profitable_count": len(self.get_profitable_positions()),
            "losing_count": len(self.get_losing_positions()),
            "near_liquidation_count": len(self.get_positions_near_liquidation()),
            "last_sync": datetime.fromtimestamp(self._last_sync).isoformat() if self._last_sync else None,
        }
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        positions_list = [p.to_dict() for p in self._positions.values()]
        
        return {
            "positions": positions_list,
            "statistics": self.get_statistics(),
            "total_value": self.get_total_position_value() + self.gateway.get_balance(),
            "available_balance": self.gateway.get_balance(),
        }


def create_position_tracker(gateway) -> PositionTracker:
    """Create position tracker"""
    return PositionTracker(gateway)
