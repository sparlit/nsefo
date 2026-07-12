import logging
try:
    from kiteconnect import KiteConnect
    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False
    KiteConnect = None
from .base import Broker
from typing import List, Dict, Any, Callable

class ZerodhaProvider(Broker):
    """
    Zerodha Kite Connect API integration.
    Auth: api_key + access_token (obtained via Kite web OAuth flow).
    Docs: https://api.kite.trade
    Package: kiteconnect (KiteConnect class)
    """

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.logger = logging.getLogger("ZerodhaProvider")
        self.kite = None
        if not _HAS_SDK:
            self.logger.error("kiteconnect package not installed. Run: pip install kiteconnect")
            return
        try:
            self.kite = KiteConnect(api_key=api_key)
            self.kite.set_access_token(access_token)
            self.logger.info("Zerodha Kite Connect Initialized.")
        except Exception as e:
            self.logger.error(f"Zerodha Init Error: {e}")
            self.kite = None

    def login(self, **kwargs) -> bool:
        if not self.kite:
            return False
        try:
            profile = self.kite.profile()
            return profile is not None
        except Exception as e:
            self.logger.error(f"Zerodha Login Failed: {e}")
            return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Returns {data: {security_id: {last_price}}}.
        Uses KiteConnect get_ltp for multiple instruments.
        Format: "exchange:tradingsymbol" e.g. "NFO:NIFTY26JUN26000PE"
        """
        if not self.kite:
            return {"status": "error"}
        try:
            # Build instrument keys from symbols
            keys = []
            for s in symbols:
                exchange = s.get("exchange_segment", "NFO")
                tradingsymbol = s.get("security_id")  # trading symbol (e.g. NIFTY26JUN26000PE)
                keys.append(f"{exchange}:{tradingsymbol}")

            ltp_data = self.kite.ltp(keys)
            results = {}
            for s in symbols:
                exchange = s.get("exchange_segment", "NFO")
                tradingsymbol = s.get("security_id")
                key = f"{exchange}:{tradingsymbol}"
                if key in ltp_data:
                    results[tradingsymbol] = {
                        "last_price": float(ltp_data[key].get("last_price", 0.0))
                    }
            return {"data": results}
        except Exception as e:
            self.logger.error(f"Zerodha Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        """
        interval: "1minute", "5minute", "15minute", "30minute", "60minute", "day"
        """
        if not self.kite:
            return []
        try:
            exchange = symbol.get("exchange_segment", "NFO")
            tradingsymbol = symbol.get("security_id")
            # Kite historical expects from_date/to_date as "YYYY-MM-DD HH:MM:SS"
            data = self.kite.historical_data(
                instrument_token=tradingsymbol,  # In Kite, this is the instrument_token (expiry token)
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                continuous=False
            )
            return data if data else []
        except Exception as e:
            self.logger.error(f"Zerodha Historical Error: {e}")
            return []

    def place_order(self, o: Dict[str, Any]) -> str:
        """
        order_details keys: exchange_segment (NFO/BFO), security_id (tradingsymbol),
                             side (BUY/SELL), quantity, order_type, price, product_type
        """
        if not self.kite:
            return ""
        try:
            exchange = o.get("exchange_segment", "NFO")
            tradingsymbol = o.get("security_id")
            transaction_type = o.get("side", "BUY").upper()
            order_type = o.get("order_type", "MARKET")
            product = o.get("product_type", "D")  # D=Delivery, M=Margin, I=Intraday

            response = self.kite.place_order(
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=int(o.get("quantity", 1)),
                order_type=order_type,
                price=o.get("price", 0),
                trigger_price=o.get("trigger_price", 0),
                product=product
            )
            if response and response.get("status") == "success":
                return str(response.get("data", {}).get("order_id", ""))
            return ""
        except Exception as e:
            self.logger.error(f"Zerodha Order Error: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.kite:
            return {}
        try:
            resp = self.kite.order_history(order_id)
            return resp[-1] if resp else {}
        except Exception as e:
            self.logger.error(f"Zerodha Order Status Error: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.kite:
            return []
        try:
            # Kite returns {'net': [...], 'day': [...]}
            resp = self.kite.positions()
            net_positions = resp.get("net", []) if resp else []
            return net_positions
        except Exception as e:
            self.logger.error(f"Zerodha Positions Error: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.kite:
            return []
        try:
            resp = self.kite.holdings()
            return resp if resp else []
        except Exception as e:
            self.logger.error(f"Zerodha Holdings Error: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        if not self.kite:
            return False
        try:
            resp = self.kite.cancel_order(order_id)
            return resp.get("status") == "success"
        except Exception as e:
            self.logger.error(f"Zerodha Cancel Order Error: {e}")
            return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """
        Zerodha uses KiteTicker (WebSocket) for real-time data.
        This method sets up the KiteTicker for the given symbols.
        """
        self.logger.info("Zerodha Real-time Feed via KiteTicker not fully implemented (requires WebSocket setup).")