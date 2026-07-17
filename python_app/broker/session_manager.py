import json
import os
import pyotp
import logging
from typing import Dict, Any

from python_app.broker_integration.factory import BrokerFactory

class SessionManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.logger = logging.getLogger("SessionManager")
        self.config = self.load_config()
        self.broker = None
        # Track discrepancy between configured mode and actual broker mode
        self._actual_mode: str = "paper"      # set by get_broker() after auth attempt
        self._mode_warning: str = ""          # non-empty = warning/alert message for dashboard
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
        if self.broker is None:
            self.broker, self._actual_mode, self._mode_warning = (
                BrokerFactory.from_config(self.config)
            )
        return self.broker

    def get_actual_mode(self) -> Dict[str, Any]:
        """
        Return actual trading mode state for the dashboard.
        Catches silent live→paper fallback so the UI can alert the user.
        """
        configured = self.config.get("mode", "paper")
        return {
            "configured": configured,
            "actual": self._actual_mode,
            "warning": self._mode_warning,
            "is_live": self._actual_mode == "live",
            "is_paper": self._actual_mode == "paper",
        }

    def ensure_logged_in(self) -> bool:
        return self.broker.login() if self.broker else False

    def automate_login(self):
        ts = self.config.get("totp_secret")
        return pyotp.TOTP(ts).now() if ts else None
