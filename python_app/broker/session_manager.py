import json
import os
import pyotp
import logging
from .dhan import DhanProvider
from .paper import PaperBroker

class SessionManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.logger = logging.getLogger("SessionManager")
        self.config = self.load_config()
        self.broker = None

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")

        default_config = {
            "mode": "live",
            "client_id": "1100625529",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzgzNjIwMDYzLCJpYXQiOjE3ODM1MzM2NjMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwNjI1NTI5In0.YoUmvceV94RSkglVGDTyvfDC2Xc2Ga7GznNhVFZ8pi7wiLZwVKzlhMfzJFCIQ_ZklomO4laT_732n33eOZ2Otg",
            "totp_secret": "",
            "risk": {
                "max_risk_per_trade_percent": 1.0,
                "daily_max_loss": 5000.0,
                "capital": 1000000.0
            }
        }
        self.save_config(default_config)
        return default_config

    def save_config(self, config):
        self.config = config
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            self.logger.info("Configuration saved successfully.")
            self.broker = None
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def update_parameters(self, new_params: dict):
        current_config = self.load_config()
        current_config.update(new_params)
        self.save_config(current_config)

    def get_broker(self):
        if not self.broker:
            mode = self.config.get("mode", "paper")
            client_id = self.config.get("client_id")
            access_token = self.config.get("access_token")

            live_provider = DhanProvider(client_id, access_token) if client_id and access_token else None

            if mode == "live" and live_provider:
                if live_provider.login():
                    self.broker = live_provider
                else:
                    self.logger.warning("Live login failed, falling back to Paper with Live Data.")
                    self.broker = PaperBroker(data_provider=live_provider)
            else:
                self.broker = PaperBroker(data_provider=live_provider)
                self.logger.info("Operating in Paper Trading Mode.")
        return self.broker

    def ensure_logged_in(self) -> bool:
        if self.broker:
            return self.broker.login()
        return False

    def automate_login(self):
        totp_secret = self.config.get("totp_secret")
        if totp_secret:
            totp = pyotp.TOTP(totp_secret)
            return totp.now()
        return None
