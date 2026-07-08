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
            "mode": "paper",
            "client_id": "",
            "access_token": "",
            "totp_secret": "",
            "risk": {
                "max_risk_per_trade_percent": 1.0,
                "daily_max_loss": 5000.0,
                "capital": 100000.0
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
            # Force broker re-initialization on next get_broker() if needed
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
            if mode == "live":
                client_id = self.config.get("client_id")
                access_token = self.config.get("access_token")
                if client_id and access_token:
                    self.broker = DhanProvider(client_id, access_token)
                    if not self.broker.login():
                        self.logger.warning("Live login failed, falling back to Paper.")
                        self.broker = PaperBroker()
                else:
                    self.logger.warning("Credentials missing for live mode, using Paper.")
                    self.broker = PaperBroker()
            else:
                self.broker = PaperBroker()
        return self.broker
