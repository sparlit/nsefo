import pyotp
import logging
from dhanhq import dhanhq, marketfeed
from .base import Broker
from typing import List, Dict, Any, Optional, Callable

class DhanProvider(Broker):
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.dhan = dhanhq(client_id, access_token)
        self.logger = logging.getLogger("DhanProvider")

    def login(self, totp_secret: str = None):
        try:
            profile = self.dhan.get_fund_limits()
            if profile.get('status') == 'success':
                self.logger.info("Dhan Login Successful")
                return True
        except Exception as e:
            self.logger.error(f"Dhan Login Failed: {e}")
        return False

    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        return self.dhan.get_quote(symbols)

    def place_order(self, o: Dict[str, Any]) -> str:
        response = self.dhan.place_order(
            tag=o.get('tag', 'NSEFO_APP'),
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
            raise Exception(f"Order failed: {response.get('remarks')}")

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return self.dhan.get_order_by_id(order_id)

    def get_positions(self) -> List[Dict[str, Any]]:
        resp = self.dhan.get_positions()
        return resp.get('data', []) if resp.get('status') == 'success' else []

    def get_holdings(self) -> List[Dict[str, Any]]:
        resp = self.dhan.get_holdings()
        return resp.get('data', []) if resp.get('status') == 'success' else []

    def cancel_order(self, order_id: str):
        return self.dhan.cancel_order(order_id)

    def start_data_feed(self, symbols: List[Dict[str, Any]], callback: Callable[[Dict[str, Any]], None]):
        """
        Uses Dhan Marketfeed for real-time WebSocket data.
        """
        instruments = [(s['exchange_segment'], s['security_id']) for s in symbols]

        feed = marketfeed.DhanFeed(
            self.client_id,
            self.access_token,
            instruments,
            marketfeed.Ticker, # or marketfeed.Quote
            callback
        )
        # Running in a separate thread would be managed by the application
        import threading
        thread = threading.Thread(target=feed.run_forever, daemon=True)
        thread.start()
