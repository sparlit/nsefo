import logging
try:
    from upstox import Upstox
    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False
    Upstox = None
from .base import Broker
from typing import List, Dict, Any, Callable

class UpstoxProvider(Broker):
    """
    Upstox Pro API integration.
    Auth: client_id + access_token.
    Docs: https://api.upstox.com/v3/
    """

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.logger = logging.getLogger("UpstoxProvider")
        self.api = None
        if not _HAS_SDK:
            self.logger.error("upstox-python package not installed. Run: pip install upstox-python")
            return
        self._authenticate()

    def _authenticate(self):
        if not _HAS_SDK:
            return
        try:
            self.api = Upstox(client_id=self.client_id, access_token=self.access_token)
            self.api.get_profile()
            self.logger.info("Upstox API Initialized.")
        except Exception as e:
            self.logger.error(f"Upstox Init Error: {e}")
            self.api = None

    def login(self, **kwargs) -> bool:
        if not self.api:
            return False
        try:
            profile = self.api.get_profile()
            return profile is not None
        except Exception as e:
            self.logger.error(f"Upstox Login Failed: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Returns {data: {security_id: {last_price}}}.
        Uses Upstox ltp endpoint for each symbol.
        """
        if not self.api:
            return {"status": "error"}
        try:
            results = {}
            for s in symbols:
                exchange = s.get("exchange_segment", "NSE_FO")  # e.g. "NSE_FO", "BSE_FO"
                symbol_token = s.get("security_id")  # Upstox uses token as security_id
                key = f"{exchange}:{symbol_token}"
                try:
                    ltp_data = self.api.get_ltp(exchange=exchange, trading_symbol=symbol_token)
                    if ltp_data and 'data' in ltp_data:
                        results[symbol_token] = {
                            "last_price": float(ltp_data['data'].get('last_price', 0.0))
                        }
                except Exception as e:
                    self.logger.debug(f"Upstox LTP error for {key}: {e}")
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Upstox Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        """
        interval: "1m", "5m", "15m", "30m", "1h", "1d"
        """
        if not self.api:
            return []
        try:
            exchange = symbol.get("exchange_segment", "NSE_FO")
            token = symbol.get("security_id")
            # Upstox historical API: get_ohlc
            data = self.api.get_ohlc(
                exchange=exchange,
                trading_symbol=token,
                interval=interval,
                from_date=from_date,
                to_date=to_date
            )
            return data if data else []
        except Exception as e:
            self.logger.error(f"Upstox Historical Error: {e}")
            return []

    def place_order(self, o: Dict[str, Any]) -> str:
        """
        order_details keys: security_id, exchange_segment, side (BUY/SELL),
                             quantity, order_type, price (optional), trigger_price (optional)
        """
        if not self.api:
            return ""
        try:
            exchange = o.get("exchange_segment", "NSE_FO")
            side = 1 if o.get("side", "BUY") == "BUY" else 2
            order_type = o.get("order_type", "MARKET")  # MARKET, LIMIT
            response = self.api.place_order(
                exchange=exchange,
                symbol=o.get("security_id"),
                transaction_type=side,
                quantity=int(o.get("quantity", 1)),
                order_type=order_type,
                price=o.get("price", 0),
                trigger_price=o.get("trigger_price", 0),
                product_type=o.get("product_type", "D"),
                validity="DAY"
            )
            if response and response.get("status") == "success":
                return str(response.get("data", {}).get("order_id", ""))
            return ""
        except Exception as e:
            self.logger.error(f"Upstox Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.api:
            return {}
        try:
            return self.api.get_order_book() or {}
        except Exception as e:
            self.logger.error(f"Upstox Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.api:
            return []
        try:
            resp = self.api.get_positions()
            return resp.get("data", []) if resp else []
        except Exception as e:
            self.logger.error(f"Upstox Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.api:
            return []
        try:
            resp = self.api.get_holdings()
            return resp.get("data", []) if resp else []
        except Exception as e:
            self.logger.error(f"Upstox Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self.api:
            return False
        try:
            resp = self.api.cancel_order(order_id)
            return resp.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Upstox Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        self.logger.info("Upstox Real-time Feed not implemented (WebSocket-based).")