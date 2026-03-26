"""
Order Manager - Async order execution with retry logic
"""
import time
import asyncio
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderTimeInForce(Enum):
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


@dataclass
class Order:
    """
    Order object
    """
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    commission: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    filled_at: Optional[float] = None
    client_order_id: Optional[str] = None
    retry_count: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price": self.avg_fill_price,
            "commission": self.commission,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.fromtimestamp(self.updated_at).isoformat(),
            "client_order_id": self.client_order_id,
        }
    
    def is_terminal(self) -> bool:
        """Check if order is in terminal state"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]


@dataclass
class OrderRequest:
    """
    Order request for the queue
    """
    request_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: OrderTimeInForce = OrderTimeInForce.GTC
    reduce_only: bool = False
    close_position: bool = False
    callback: Optional[Callable] = None
    priority: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)


class OrderManager:
    """
    Async Order Manager with retry logic
    """
    
    def __init__(self, gateway, max_concurrent: int = 5, order_timeout: float = 30.0):
        self.gateway = gateway
        self.max_concurrent = max_concurrent
        self.order_timeout = order_timeout
        
        self._orders: Dict[str, Order] = {}
        self._pending_orders: Dict[str, Order] = {}
        self._order_queue: List[OrderRequest] = []
        self._lock = Lock()
        
        self._active_orders: int = 0
        self._total_orders: int = 0
        self._filled_orders: int = 0
        self._rejected_orders: int = 0
        
        self._order_id_counter: int = 1
        
        self._callbacks: Dict[str, Callable] = {}
        
        logger.info("Order Manager initialized")
    
    def generate_order_id(self) -> str:
        """Generate unique order ID"""
        with self._lock:
            order_id = f"GM_{int(time.time()*1000)}_{self._order_id_counter}"
            self._order_id_counter += 1
            return order_id
    
    def generate_client_order_id(self) -> str:
        """Generate client order ID"""
        return f"GM_{int(time.time()*1000)}"
    
    async def submit_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        callback: Callable = None
    ) -> Order:
        """Submit market order"""
        request = OrderRequest(
            request_id=self.generate_order_id(),
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            callback=callback
        )
        return await self._submit_order(request)
    
    async def submit_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        callback: Callable = None
    ) -> Order:
        """Submit limit order"""
        request = OrderRequest(
            request_id=self.generate_order_id(),
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            callback=callback
        )
        return await self._submit_order(request)
    
    async def submit_stop_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_price: float,
        callback: Callable = None
    ) -> Order:
        """Submit stop order"""
        request = OrderRequest(
            request_id=self.generate_order_id(),
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP,
            quantity=quantity,
            stop_price=stop_price,
            callback=callback
        )
        return await self._submit_order(request)
    
    async def _submit_order(self, request: OrderRequest) -> Order:
        """Submit order to exchange"""
        order_id = request.request_id
        
        client_order_id = self.generate_client_order_id()
        
        order = Order(
            order_id=order_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            status=OrderStatus.PENDING,
            client_order_id=client_order_id
        )
        
        with self._lock:
            self._orders[order_id] = order
            self._pending_orders[order_id] = order
            self._total_orders += 1
        
        logger.info(f"Submitting order: {order_id} {request.side.value} {request.quantity} {request.symbol}")
        
        success = await self._execute_order(order, request)
        
        if success:
            order.status = OrderStatus.SUBMITTED
            order.updated_at = time.time()
            self._filled_orders += 1
            logger.info(f"Order filled: {order_id}")
        else:
            order.status = OrderStatus.REJECTED
            order.updated_at = time.time()
            self._rejected_orders += 1
            logger.error(f"Order rejected: {order_id}")
        
        if request.callback:
            try:
                request.callback(order)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        with self._lock:
            if order_id in self._pending_orders:
                del self._pending_orders[order_id]
        
        return order
    
    async def _execute_order(self, order: Order, request: OrderRequest) -> bool:
        """Execute order via gateway"""
        from exchange.binance_gateway import BinanceGateway, OrderSide as BinanceOrderSide, OrderType as BinanceOrderType, PositionSide
        
        try:
            if order.order_type == OrderType.MARKET:
                result = self.gateway.place_market_order(
                    symbol=order.symbol,
                    side=BinanceOrderSide[order.side.name],
                    quantity=order.quantity,
                )
            elif order.order_type == OrderType.LIMIT:
                result = self.gateway.place_limit_order(
                    symbol=order.symbol,
                    side=BinanceOrderSide[order.side.name],
                    quantity=order.quantity,
                    price=order.price,
                )
            elif order.order_type == OrderType.STOP:
                result = self.gateway.place_stop_order(
                    symbol=order.symbol,
                    side=BinanceOrderSide[order.side.name],
                    quantity=order.quantity,
                    stop_price=order.stop_price,
                )
            else:
                logger.error(f"Unsupported order type: {order.order_type}")
                return False
            
            if result.get('orderId'):
                order.avg_fill_price = float(result.get('avgPrice', order.price or 0))
                order.filled_quantity = float(result.get('executedQty', 0))
                order.status = OrderStatus.FILLED
                order.filled_at = time.time()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            order.error = str(e)
            
            if request.retry_count < request.max_retries:
                request.retry_count += 1
                retry_delay = 2 ** request.retry_count
                logger.info(f"Retrying order {order.order_id} in {retry_delay}s (attempt {request.retry_count})")
                await asyncio.sleep(retry_delay)
                return await self._execute_order(order, request)
            
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        with self._lock:
            if order_id not in self._orders:
                logger.warning(f"Order {order_id} not found")
                return False
            
            order = self._orders[order_id]
            
            if order.is_terminal():
                logger.warning(f"Order {order_id} already in terminal state: {order.status}")
                return False
        
        try:
            result = self.gateway.cancel_order(order.symbol, order_id=order.order_id)
            
            with self._lock:
                order.status = OrderStatus.CANCELLED
                order.updated_at = time.time()
                
                if order_id in self._pending_orders:
                    del self._pending_orders[order_id]
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all open orders for symbol"""
        try:
            result = self.gateway.cancel_all_orders(symbol)
            cancelled = len(result.get('orderIds', []))
            logger.info(f"Cancelled {cancelled} orders for {symbol}")
            return cancelled
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return 0
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def get_open_orders(self, symbol: str = None) -> List[Order]:
        """Get open orders"""
        with self._lock:
            orders = list(self._pending_orders.values())
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        return orders
    
    def get_filled_orders(self, symbol: str = None, since: float = None) -> List[Order]:
        """Get filled orders"""
        orders = [o for o in self._orders.values() if o.status == OrderStatus.FILLED]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        if since:
            orders = [o for o in orders if o.created_at >= since]
        
        return orders
    
    def get_statistics(self) -> Dict:
        """Get order statistics"""
        with self._lock:
            return {
                "total_orders": self._total_orders,
                "pending_orders": len(self._pending_orders),
                "filled_orders": self._filled_orders,
                "rejected_orders": self._rejected_orders,
                "fill_rate": self._filled_orders / max(1, self._total_orders),
                "active_orders": self._active_orders,
            }
    
    def sync_orders(self):
        """Sync orders with exchange"""
        try:
            for symbol in set(o.symbol for o in self._pending_orders.values()):
                exchange_orders = self.gateway.get_open_orders(symbol)
                
                with self._lock:
                    for ex_order in exchange_orders:
                        order_id = str(ex_order['orderId'])
                        if order_id in self._orders:
                            order = self._orders[order_id]
                            order.filled_quantity = float(ex_order.get('executedQty', 0))
                            order.avg_fill_price = float(ex_order.get('avgPrice', 0))
                            
                            if order.filled_quantity >= order.quantity:
                                order.status = OrderStatus.FILLED
                                order.filled_at = time.time()
                            elif order.filled_quantity > 0:
                                order.status = OrderStatus.PARTIALLY_FILLED
                            
                            order.updated_at = time.time()
            
            logger.debug("Orders synced with exchange")
            
        except Exception as e:
            logger.error(f"Failed to sync orders: {e}")


def create_order_manager(gateway) -> OrderManager:
    """Create order manager"""
    return OrderManager(gateway)
