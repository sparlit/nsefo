import pyotp
import logging
from dhanhq import dhanhq
from .base import Broker
from typing import List, Dict, Any, Optional

class DhanProvider(Broker):
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.dhan = dhanhq(client_id, access_token)
        self.logger = logging.getLogger("DhanProvider")

    def login(self, totp_secret: str = None):
        """
        Dhan access tokens are typically valid for a long period.
        If a session needs to be refreshed via TOTP, it would be handled here.
        """
        try:
            profile = self.dhan.get_fund_limits()
            if profile.get('status') == 'success':
                self.logger.info("Dhan Login Successful")
                return True
        except Exception as e:
            self.logger.error(f"Dhan Login Failed: {e}")
        return False

    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Returns snapshot data for provided symbols.
        Dhan get_quote takes security_id and exchange_segment.
        For simplicity in this expert app, we assume symbols are passed as dicts
        or we handle the mapping internally.
        """
        # Example: symbols = [{'security_id': '1333', 'exchange_segment': 'NSE_EQ'}]
        return self.dhan.get_quote(symbols)

    def place_order(self, o: Dict[str, Any]) -> str:
        """
        o contains: symbol, qty, side, type, price, etc.
        """
        response = self.dhan.place_order(
            tag=o.get('tag', 'NSEFO_APP'),
            transaction_type=o.get('side', 'BUY'), # BUY or SELL
            exchange_segment=o.get('exchange_segment', 'NSE_FNO'),
            product_type=o.get('product_type', 'MARGIN'),
            order_type=o.get('order_type', 'MARKET'),
            validity='DAY',
            security_id=str(o.get('security_id')),
            quantity=int(o.get('quantity')),
            price=float(o.get('price', 0)),
            trigger_price=float(o.get('trigger_price', 0)),
            drv_expiry_date=o.get('expiry_date'),
            drv_options_type=o.get('option_type'),
            drv_strike_price=o.get('strike_price')
        )
        if response.get('status') == 'success':
            return response['data']['orderId']
        else:
            raise Exception(f"Order placement failed: {response.get('remarks')}")

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
