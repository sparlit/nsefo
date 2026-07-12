import json
import os
import pyotp
import logging
from .dhan import DhanProvider
from .paper import PaperBroker
from .fenix_broker import FenixDhanProvider
# ── 15 new broker providers ──────────────────────────────────────────────
from .aliceblue import AliceBlueProvider
from .angelone import AngelOneProvider
from .choice import ChoiceProvider
from .finvasia import FinvasiaProvider
from .fivepaisa import FivePaisaProvider
from .fyers import FyersProvider
from .iifl import IIFLProvider
from .kotak import KotakProvider
from .kotak_neo import KotakNeoProvider
from .kunjee import KunjeeProvider
from .master_trust import MasterTrustProvider
from .motilal import MotilalProvider
from .upstox import UpstoxProvider
from .vpc import VPCProvider
from .zerodha import ZerodhaProvider
from .moneysukh import MoneysukhProvider
from .hdfc import HDFCSecuritiesProvider
from .icici import ICICIDirectProvider
from .sbi import SBISecuritiesProvider
from .bajaj import BajajFinancialProvider
from .geojit import GeojitProvider
from .sharekhan import SharekhanProvider
from .anand_rathi import AnandRathiProvider
from .edelweiss import EdelweissProvider
from .nirmal_bang import NirmalBangProvider
from .axis_direct import AxisDirectProvider
from .groww import GrowwProvider
from .paytm_money import PaytmMoneyProvider
from .mstock import MStockProvider

class SessionManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.logger = logging.getLogger("SessionManager")
        self.config = self.load_config()
        self.broker = None
        # TokenManager — centralized token storage + auto-relogin on 401
        self._token_manager = None
        try:
            from python_app.auth.browser_login import TokenManager
            self._token_manager = TokenManager()
            self.logger.info("TokenManager ready — auto-relogin enabled")
        except ImportError:
            self.logger.warning("browser_login.py not found — auto-relogin disabled (pip install playwright)")

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    cfg = json.load(f)
                    if "fixed_lots" not in cfg["risk"]: cfg["risk"]["fixed_lots"] = 1
                    return cfg
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")

        default_config = {
            "mode": "paper",
            "provider": "",
            "client_id": "",
            "access_token": "",
            "totp_secret": "",
            "target_frequency": "scalping",
            "data_provider": "",
            "risk": {
                "max_risk_per_trade_percent": 1.0,
                "daily_max_loss": 5000.0,
                "capital": 1000000.0,
                "fixed_lots": 1
            }
        }
        self.save_config(default_config)
        return default_config

    def save_config(self, config):
        self.config = config
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            self.logger.info("Configuration Persisted.")
            self.broker = None
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def get_broker(self):
        if not self.broker:
            mode = self.config.get("mode", "paper")
            client_id = self.config.get("client_id")
            access_token = self.config.get("access_token")
            provider_type = self.config.get("provider", "fenix")

            if provider_type == "fenix":
                live_provider = FenixDhanProvider(client_id, access_token)
            elif provider_type == "aliceblue":
                live_provider = AliceBlueProvider(client_id, access_token)
            elif provider_type == "angelone":
                live_provider = AngelOneProvider(client_id, access_token)
            elif provider_type == "choice":
                live_provider = ChoiceProvider(client_id, access_token)
            elif provider_type == "finvasia":
                live_provider = FinvasiaProvider(client_id, access_token)
            elif provider_type == "5paisa":
                live_provider = FivePaisaProvider(client_id, access_token)
            elif provider_type == "fyers":
                live_provider = FyersProvider(client_id, access_token)
            elif provider_type == "iifl":
                live_provider = IIFLProvider(client_id, access_token)
            elif provider_type == "kotak":
                live_provider = KotakProvider(client_id, access_token)
            elif provider_type == "kotak_neo":
                live_provider = KotakNeoProvider(client_id, access_token)
            elif provider_type == "kunjee":
                live_provider = KunjeeProvider(client_id, access_token)
                self.logger.warning(
                    "Kunjee API base URL is unverified and SSRF-blocked. "
                    "DEPRECATED — use a supported broker."
                )
            elif provider_type == "master_trust":
                live_provider = MasterTrustProvider(client_id, access_token)
            elif provider_type == "motilal":
                live_provider = MotilalProvider(client_id, access_token)
            elif provider_type == "upstox":
                live_provider = UpstoxProvider(client_id, access_token)
            elif provider_type == "vpc":
                live_provider = VPCProvider(client_id, access_token)
                if getattr(live_provider, "DEPRECATED", False):
                    self.logger.warning(
                        "VPC is DEPRECATED (api.vpcapis.com returns 404). "
                        "Switch to a supported broker."
                    )
            elif provider_type == "zerodha":
                live_provider = ZerodhaProvider(api_key=self.config.get("api_key", ""), access_token=access_token)
            elif provider_type == "moneysukh":
                live_provider = MoneysukhProvider(client_id, access_token, api_key=self.config.get("api_key", ""))
            elif provider_type == "hdfc":
                live_provider = HDFCSecuritiesProvider(client_id, access_token)
            elif provider_type == "icici":
                live_provider = ICICIDirectProvider(
                    client_id=client_id,
                    api_key=self.config.get("api_key", ""),
                    access_token=access_token,
                    refresh_token=self.config.get("refresh_token", ""),
                    client_secret=self.config.get("client_secret", ""),
                )
            elif provider_type == "sbi":
                live_provider = SBISecuritiesProvider(app_name=client_id, access_token=access_token)
            elif provider_type == "bajaj":
                live_provider = BajajFinancialProvider(api_key=self.config.get("api_key", ""), client_id=client_id, access_token=access_token)
            elif provider_type == "geojit":
                live_provider = GeojitProvider(
                    client_id=client_id,
                    password=self.config.get("password", ""),
                    yob=self.config.get("yob", ""),
                    access_token=access_token,
                )
            elif provider_type == "sharekhan":
                live_provider = SharekhanProvider(client_id, access_token)
            elif provider_type == "anand_rathi":
                live_provider = AnandRathiProvider(client_id, access_token)
            elif provider_type == "edelweiss":
                live_provider = EdelweissProvider(client_id, access_token)
            elif provider_type == "nirmal_bang":
                live_provider = NirmalBangProvider(
                    client_id, access_token, api_key=self.config.get("api_key", "")
                )
            elif provider_type == "axis_direct":
                live_provider = AxisDirectProvider(client_id, access_token)
            elif provider_type == "groww":
                live_provider = GrowwProvider(api_key=self.config.get("api_key", ""), access_token=access_token)
            elif provider_type == "paytm_money":
                live_provider = PaytmMoneyProvider(
                    client_id=client_id,
                    client_secret=self.config.get("client_secret", ""),
                    access_token=access_token,
                )
                if getattr(live_provider, "DEPRECATED", False):
                    self.logger.warning(
                        "Paytm Money: F&O segment NOT confirmed. "
                        "Use Zerodha, AngelOne, or Dhan for options trading."
                    )
            elif provider_type == "mstock":
                live_provider = MStockProvider(
                    client_id=client_id,
                    access_token=access_token,
                    api_key=self.config.get("api_key", ""),
                )
            else:
                live_provider = DhanProvider(client_id, access_token)

            if mode == "live":
                if live_provider.login():
                    self.broker = live_provider
                else:
                    self.logger.warning("Live Auth Failed, Fallback to Paper-with-Live-Data.")
                    self.broker = PaperBroker(data_provider=live_provider)
            else:
                self.broker = PaperBroker(data_provider=live_provider)
        return self.broker

    def ensure_logged_in(self) -> bool:
        return self.broker.login() if self.broker else False

    def automate_login(self):
        ts = self.config.get("totp_secret")
        return pyotp.TOTP(ts).now() if ts else None
