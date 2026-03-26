"""
Binance WebSocket for real-time market data
"""
import json
import asyncio
import logging
import threading
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum
import websockets
from websockets.client import connect

logger = logging.getLogger(__name__)


class BinanceWebSocketConfig:
    """WebSocket Configuration"""
    
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        
        if testnet:
            self.ws_url = "wss://stream.testnet.binance.vision/stream"
        else:
            self.ws_url = "wss://fstream.binance.com/stream"


class StreamType(Enum):
    TICKER = "ticker"
    KLINE = "kline"
    TRADE = "trade"
    DEPTH = "depth"
    BOOK_TICKER = "bookTicker"


@dataclass
class TickerData:
    """24hr Ticker Data"""
    symbol: str
    price_change: float
    price_change_percent: float
    last_price: float
    high_price: float
    low_price: float
    volume: float
    quote_volume: float
    open_price: float
    open_time: int
    close_time: int


@dataclass
class KlineData:
    """Kline/Candlestick Data"""
    symbol: str
    interval: str
    start_time: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    close_time: int
    is_closed: bool


@dataclass
class TradeData:
    """Trade Data"""
    symbol: str
    trade_id: int
    price: float
    quantity: float
    buyer_order_id: int
    seller_order_id: int
    timestamp: int
    is_buyer_maker: bool


class BinanceWebSocket:
    """
    Binance Futures WebSocket Manager
    """
    
    def __init__(self, config: BinanceWebSocketConfig = None):
        self.config = config or BinanceWebSocketConfig()
        self.ws = None
        self.is_connected = False
        self.subscriptions: List[str] = []
        
        self._ticker_callbacks: List[Callable] = []
        self._kline_callbacks: List[Callable] = []
        self._trade_callbacks: List[Callable] = []
        
        self._thread = None
        self._running = False
        self._reconnect_delay = 1
        self._max_reconnect_delay = 30
        
        logger.info(f"Binance WebSocket initialized (testnet: {self.config.testnet})")
    
    def subscribe_ticker(self, symbol: str, callback: Callable[[TickerData], None]):
        """Subscribe to ticker stream"""
        stream = f"{symbol.lower()}@ticker"
        self.subscriptions.append(stream)
        self._ticker_callbacks.append(callback)
        logger.info(f"Subscribed to ticker: {symbol}")
    
    def subscribe_kline(self, symbol: str, callback: Callable[[KlineData], None], interval: str = "1m"):
        """Subscribe to kline stream"""
        stream = f"{symbol.lower()}@kline_{interval}"
        self.subscriptions.append(stream)
        self._kline_callbacks.append(callback)
        logger.info(f"Subscribed to kline: {symbol} {interval}")
    
    def subscribe_trades(self, symbol: str, callback: Callable[[TradeData], None]):
        """Subscribe to trade stream"""
        stream = f"{symbol.lower()}@trade"
        self.subscriptions.append(stream)
        self._trade_callbacks.append(callback)
        logger.info(f"Subscribed to trades: {symbol}")
    
    def subscribe_mark_price(self, symbol: str, callback: Callable[[float], None]):
        """Subscribe to mark price stream"""
        stream = f"{symbol.lower()}@markPrice"
        self.subscriptions.append(stream)
        logger.info(f"Subscribed to mark price: {symbol}")
    
    def connect(self):
        """Connect to WebSocket in background thread"""
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("WebSocket connection started in background")
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self._running = False
        self._reconnect_delay = 1
        if self.ws:
            asyncio.run(self._close())
        logger.info("WebSocket disconnected")
    
    async def _close(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.ws = None
        self.is_connected = False
    
    async def _connect_and_subscribe(self):
        """Connect and subscribe to streams"""
        try:
            self.ws = await connect(self.config.ws_url)
            self.is_connected = True
            self._reconnect_delay = 1
            logger.info("WebSocket connected")
            
            if self.subscriptions:
                subscribe_msg = {
                    "method": "SUBSCRIBE",
                    "params": self.subscriptions,
                    "id": 1
                }
                await self.ws.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to {len(self.subscriptions)} streams")
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.is_connected = False
            return False
    
    def _run(self):
        """Run WebSocket in background"""
        asyncio.run(self._run_async())
    
    async def _run_async(self):
        """Async WebSocket loop"""
        while self._running:
            if not self.is_connected:
                success = await self._connect_and_subscribe()
                if not success:
                    logger.warning(f"Reconnecting in {self._reconnect_delay}s...")
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        self._max_reconnect_delay
                    )
                    continue
            
            try:
                async for message in self.ws:
                    if not self._running:
                        break
                    self._process_message(message)
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                self.is_connected = False
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.is_connected = False
    
    def _process_message(self, message: str):
        """Process WebSocket message"""
        try:
            data = json.loads(message)
            
            if 'data' in data:
                stream_data = data['data']
                event_type = stream_data.get('e')
                
                if event_type == '24hrTicker':
                    self._handle_ticker(stream_data)
                elif event_type == 'kline':
                    self._handle_kline(stream_data)
                elif event_type == 'trade':
                    self._handle_trade(stream_data)
                elif event_type == 'markPriceUpdate':
                    self._handle_mark_price(stream_data)
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    def _handle_ticker(self, data: Dict):
        """Handle ticker data"""
        ticker = TickerData(
            symbol=data['s'],
            price_change=float(data['p']),
            price_change_percent=float(data['P']),
            last_price=float(data['c']),
            high_price=float(data['h']),
            low_price=float(data['l']),
            volume=float(data['v']),
            quote_volume=float(data['q']),
            open_price=float(data['o']),
            open_time=data['o'],
            close_time=data['C']
        )
        
        for callback in self._ticker_callbacks:
            try:
                callback(ticker)
            except Exception as e:
                logger.error(f"Ticker callback error: {e}")
    
    def _handle_kline(self, data: Dict):
        """Handle kline data"""
        k = data['k']
        kline = KlineData(
            symbol=k['s'],
            interval=k['i'],
            start_time=k['t'],
            open_price=float(k['o']),
            high_price=float(k['h']),
            low_price=float(k['l']),
            close_price=float(k['c']),
            volume=float(k['v']),
            close_time=k['T'],
            is_closed=k['x']
        )
        
        for callback in self._kline_callbacks:
            try:
                callback(kline)
            except Exception as e:
                logger.error(f"Kline callback error: {e}")
    
    def _handle_trade(self, data: Dict):
        """Handle trade data"""
        trade = TradeData(
            symbol=data['s'],
            trade_id=data['t'],
            price=float(data['p']),
            quantity=float(data['q']),
            buyer_order_id=data['b'],
            seller_order_id=data['a'],
            timestamp=data['T'],
            is_buyer_maker=data['m']
        )
        
        for callback in self._trade_callbacks:
            try:
                callback(trade)
            except Exception as e:
                logger.error(f"Trade callback error: {e}")
    
    def _handle_mark_price(self, data: Dict):
        """Handle mark price update"""
        mark_price = float(data['p'])
        logger.debug(f"Mark price update: {data['s']} = {mark_price}")
    
    def check_connected(self) -> bool:
        """Check if connected"""
        return self.is_connected


def create_websocket(testnet: bool = True) -> BinanceWebSocket:
    """Create Binance WebSocket"""
    config = BinanceWebSocketConfig(testnet=testnet)
    return BinanceWebSocket(config)
