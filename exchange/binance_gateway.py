"""
Binance Futures Gateway
REST API wrapper for Binance Futures trading
"""
import os
import time
import hmac
import hashlib
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class BinanceConfig:
    """Binance API Configuration"""
    
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        testnet: bool = True,
        recv_window: int = 5000
    ):
        self.api_key = api_key or os.getenv('BINANCE_API_KEY', '')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET', '')
        self.testnet = testnet
        self.recv_window = recv_window
        
        if testnet:
            self.base_url = "https://testnet.binancefuture.com"
            self.ws_url = "wss://stream.testnet.binance.vision/stream"
        else:
            self.base_url = "https://fapi.binance.com"
            self.ws_url = "wss://fstream.binance.com/stream"
        
        self.headers = {
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/json"
        }


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


class BinanceGateway:
    """
    Binance Futures REST API Gateway
    """
    
    def __init__(self, config: BinanceConfig = None):
        self.config = config or BinanceConfig()
        self.session = requests.Session()
        self.session.headers.update(self.config.headers)
        
        logger.info(f"Binance Gateway initialized (testnet: {self.config.testnet})")
    
    def _generate_signature(self, params: str) -> str:
        """Generate HMAC SHA256 signature"""
        return hmac.new(
            self.config.api_secret.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        signed: bool = True
    ) -> Dict:
        """Make signed API request"""
        if params is None:
            params = {}
        
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = self.config.recv_window
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        
        if signed and self.config.api_secret:
            signature = self._generate_signature(query_string)
            query_string += f"&signature={signature}"
        
        url = f"{self.config.base_url}{endpoint}?{query_string}"
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=self.config.headers)
            elif method == "POST":
                response = self.session.post(url, headers=self.config.headers)
            elif method == "DELETE":
                response = self.session.delete(url, headers=self.config.headers)
            elif method == "PUT":
                response = self.session.put(url, headers=self.config.headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') or result.get('msg'):
                logger.error(f"Binance API error: {result}")
                raise Exception(f"API Error: {result.get('msg', 'Unknown')}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _public_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make public API request"""
        if params is None:
            params = {}
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{self.config.base_url}{endpoint}?{query_string}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Public request failed: {e}")
            raise
    
    # ==================== Market Data ====================
    
    def get_server_time(self) -> int:
        """Get server time"""
        return self._public_request("/fapi/v1/time")['serverTime']
    
    def get_exchange_info(self, symbol: str = None) -> Dict:
        """Get exchange information"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._public_request("/fapi/v1/exchangeInfo", params)
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get symbol information"""
        info = self.get_exchange_info(symbol)
        for s in info.get('symbols', []):
            if s['symbol'] == symbol:
                return s
        return {}
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker"""
        return self._public_request("/fapi/v1/ticker/24hr", {"symbol": symbol})
    
    def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """Get order book"""
        return self._public_request("/fapi/v1/depth", {"symbol": symbol, "limit": limit})
    
    def get_recent_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Get recent trades"""
        return self._public_request("/fapi/v1/trades", {"symbol": symbol, "limit": limit})
    
    def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 500
    ) -> List[List]:
        """Get kline/candlestick data"""
        return self._public_request("/fapi/v1/klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })
    
    def get_mark_price(self, symbol: str) -> Dict:
        """Get mark price"""
        return self._public_request("/fapi/v1/premiumIndex", {"symbol": symbol})
    
    def get_funding_rate(self, symbol: str) -> Dict:
        """Get funding rate"""
        return self._public_request("/fapi/v1/fundingRate", {"symbol": symbol})
    
    # ==================== Account ====================
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        return self._signed_request("GET", "/fapi/v2/account")
    
    def get_balance(self, asset: str = "USDT") -> float:
        """Get balance for asset"""
        account = self.get_account_info()
        for balance in account.get('assets', []):
            if balance['asset'] == asset:
                return float(balance['availableBalance'])
        return 0.0
    
    def get_positions(self) -> List[Dict]:
        """Get all positions"""
        account = self.get_account_info()
        positions = []
        for pos in account.get('positions', []):
            if float(pos.get('positionAmt', 0)) != 0:
                positions.append({
                    'symbol': pos['symbol'],
                    'positionAmt': float(pos['positionAmt']),
                    'entryPrice': float(pos['entryPrice']),
                    'markPrice': float(pos['markPrice']),
                    'unrealizedProfit': float(pos['unrealizedProfit']),
                    'positionSide': pos.get('positionSide', 'BOTH'),
                    'leverage': int(pos['leverage']),
                    'isolatedMargin': float(pos.get('isolatedMargin', 0)),
                })
        return positions
    
    def get_position_info(self, symbol: str) -> Dict:
        """Get position info for symbol"""
        positions = self.get_positions()
        for pos in positions:
            if pos['symbol'] == symbol:
                return pos
        return {}
    
    # ==================== Orders ====================
    
    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float = None,
        stop_price: float = None,
        position_side: PositionSide = PositionSide.BOTH,
        reduce_only: bool = False,
        close_position: bool = False,
        activation_price: float = None,
        callback_rate: float = None
    ) -> Dict:
        """
        Create a new order
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP, TAKE_PROFIT, TRAILING_STOP
            quantity: Order quantity
            price: Limit price (for LIMIT orders)
            stop_price: Stop price (for STOP/TAKE_PROFIT)
            position_side: LONG, SHORT, or BOTH
            reduce_only: Only reduce position
            close_position: Close entire position
            activation_price: Activation price (for TRAILING_STOP)
            callback_rate: Callback rate % (for TRAILING_STOP)
        """
        params = {
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "quantity": quantity,
            "positionSide": position_side.value,
        }
        
        if price:
            params['price'] = price
            params['timeInForce'] = 'GTC'
        
        if stop_price:
            params['stopPrice'] = stop_price
        
        if reduce_only:
            params['reduceOnly'] = 'true'
        
        if close_position:
            params['closePosition'] = 'true'
        
        if activation_price:
            params['activationPrice'] = activation_price
        
        if callback_rate:
            params['callbackRate'] = callback_rate
        
        return self._signed_request("POST", "/fapi/v1/order", params)
    
    def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        position_side: PositionSide = PositionSide.BOTH,
        reduce_only: bool = False
    ) -> Dict:
        """Place market order"""
        return self.create_order(
            symbol, side, OrderType.MARKET, quantity,
            position_side=position_side, reduce_only=reduce_only
        )
    
    def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        position_side: PositionSide = PositionSide.BOTH
    ) -> Dict:
        """Place limit order"""
        return self.create_order(
            symbol, side, OrderType.LIMIT, quantity, price=price,
            position_side=position_side
        )
    
    def place_stop_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_price: float,
        position_side: PositionSide = PositionSide.BOTH
    ) -> Dict:
        """Place stop order"""
        return self.create_order(
            symbol, side, OrderType.STOP, quantity, stop_price=stop_price,
            position_side=position_side
        )
    
    def place_trailing_stop(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        activation_price: float,
        callback_rate: float = 0.5,
        position_side: PositionSide = PositionSide.BOTH
    ) -> Dict:
        """Place trailing stop order"""
        return self.create_order(
            symbol, side, OrderType.TRAILING_STOP, quantity,
            activation_price=activation_price, callback_rate=callback_rate,
            position_side=position_side
        )
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get open orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._signed_request("GET", "/fapi/v1/openOrders", params)
    
    def get_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None) -> Dict:
        """Get order by ID"""
        params = {"symbol": symbol}
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        return self._signed_request("GET", "/fapi/v1/order", params)
    
    def cancel_order(self, symbol: str, order_id: int = None, orig_client_order_id: str = None) -> Dict:
        """Cancel order"""
        params = {"symbol": symbol}
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        return self._signed_request("DELETE", "/fapi/v1/order", params)
    
    def cancel_all_orders(self, symbol: str) -> List[Dict]:
        """Cancel all open orders for symbol"""
        return self._signed_request("DELETE", "/fapi/v1/allOpenOrders", {"symbol": symbol})
    
    def close_position(self, symbol: str) -> Dict:
        """Close entire position"""
        return self.create_order(
            symbol,
            OrderSide.SELL if self.get_position_info(symbol).get('positionAmt', 0) > 0 else OrderSide.BUY,
            OrderType.MARKET,
            abs(self.get_position_info(symbol).get('positionAmt', 0)),
            close_position=True
        )
    
    # ==================== Leverage & Margin ====================
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """Set leverage for symbol"""
        return self._signed_request("POST", "/fapi/v1/leverage", {
            "symbol": symbol,
            "leverage": leverage
        })
    
    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> Dict:
        """Set margin type (ISOLATED or CROSSED)"""
        return self._signed_request("POST", "/fapi/v1/marginType", {
            "symbol": symbol,
            "marginType": margin_type
        })
    
    # ==================== Trading Utilities ====================
    
    def get_min_quantity(self, symbol: str) -> float:
        """Get minimum order quantity"""
        info = self.get_symbol_info(symbol)
        for filter in info.get('filters', []):
            if filter['filterType'] == 'LOT_SIZE':
                return float(filter['minQty'])
        return 0.001
    
    def get_price_precision(self, symbol: str) -> int:
        """Get price precision"""
        info = self.get_symbol_info(symbol)
        return int(info.get('pricePrecision', 2))
    
    def get_quantity_precision(self, symbol: str) -> int:
        """Get quantity precision"""
        info = self.get_symbol_info(symbol)
        return int(info.get('quantityPrecision', 3))
    
    def calculate_liquidation_price(
        self,
        symbol: str,
        position_side: PositionSide,
        entry_price: float,
        quantity: float,
        leverage: int,
        wallet_balance: float,
        isolated_margin: float = 0
    ) -> float:
        """Calculate liquidation price"""
        info = self.get_symbol_info(symbol)
        maintenance_margin_rate = 0.005
        
        for filter in info.get('filters', []):
            if filter['filterType'] == 'MAINTENANCE_MARGIN':
                maintenance_margin_rate = float(filter['maintenanceMarginRate'])
                break
        
        if position_side == PositionSide.LONG:
            liq_price = entry_price * (1 - (leverage / 100) + maintenance_margin_rate)
        else:
            liq_price = entry_price * (1 + (leverage / 100) - maintenance_margin_rate)
        
        return liq_price
    
    def get_wallet_balance(self) -> Dict:
        """Get full wallet balance info"""
        account = self.get_account_info()
        balances = {}
        for asset in account.get('assets', []):
            balances[asset['asset']] = {
                'wallet_balance': float(asset['walletBalance']),
                'available_balance': float(asset['availableBalance']),
                'total_unrealized_pnl': float(asset['totalUnrealizedProfit']),
            }
        return balances


# Convenience function
def create_gateway(testnet: bool = True) -> BinanceGateway:
    """Create Binance gateway with config"""
    config = BinanceConfig(testnet=testnet)
    return BinanceGateway(config)
