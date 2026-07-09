import logging
import traceback
from dhanhq import dhanhq, DhanContext
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

class DhanProvider(Broker):
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.logger = logging.getLogger("DhanProvider")
        try:
            context = DhanContext(client_id, access_token)
            self.dhan = dhanhq(context)
        except Exception as e:
            self.logger.error(f"Critical SDK Initialization Error: {e}")
            self.dhan = None

    def login(self, **kwargs) -> bool:
        if not self.dhan: return False
        try:
            profile = self.dhan.get_fund_limits()
            if profile.get('status') == 'success':
                self.logger.info(f"Dhan Account {self.client_id} Connected.")
                return True
        except Exception as e:
            self.logger.error(f"Dhan Auth Failed: {e}")
        return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        try:
            return self.dhan.quote_data(symbols)
        except Exception as e:
            self.logger.error(f"Market Data Error: {e}")
            return {"status": "error", "remarks": str(e)}

    def get_historical_data(self, symbol: Dict[str, str], interval: str, from_date: str, to_date: str) -> Any:
        try:
            return self.dhan.intraday_minute_data(
                security_id=symbol['security_id'],
                exchange_segment=symbol['exchange_segment'],
                instrument_type='EQUITY'
            )
        except Exception as e:
            self.logger.error(f"Historical Data Error: {e}")
            return []

    def place_order(self, o: Dict[str, Any]) -> str:
        try:
            response = self.dhan.place_order(
                tag=o.get('tag', 'NSEFO_PRO'),
                transaction_type=o.get('side', 'BUY'),
                exchange_segment=o.get('exchange_segment', 'NSE_FNO'),
                product_type=o.get('product_type', 'MARGIN'),
                order_type=o.get('order_type', 'MARKET'),
                validity='DAY',
                security_id=str(o.get('security_id')),
                quantity=int(o.get('quantity')),
                price=float(o.get('price', 0)),
                trigger_price=float(o.get('trigger_price', 0))
            )
            if response.get('status') == 'success':
                return response['data']['orderId']
            else:
                self.logger.warning(f"Order Rejected: {response.get('remarks')}")
                return ""
        except Exception as e:
            self.logger.error(f"Order Execution Exception: {e}")
            return ""

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try: return self.dhan.get_order_by_id(order_id)
        except: return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        try:
            resp = self.dhan.get_positions()
            return resp.get('data', []) if resp.get('status') == 'success' else []
        except: return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        try:
            resp = self.dhan.get_holdings()
            return resp.get('data', []) if resp.get('status') == 'success' else []
        except: return []

    def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self.dhan.cancel_order(order_id)
            return resp.get('status') == 'success'
        except: return False

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        from dhanhq import marketfeed
        try:
            instruments = [(s['exchange_segment'], s['security_id']) for s in symbols]
            feed = marketfeed.DhanFeed(self.client_id, self.access_token, instruments, marketfeed.Ticker, callback)
            import threading
            threading.Thread(target=feed.run_forever, daemon=True, name="DhanFeedThread").start()
        except Exception as e:
            self.logger.error(f"Feed Start Failure: {e}")
