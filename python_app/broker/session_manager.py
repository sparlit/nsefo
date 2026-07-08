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
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"mode": "paper", "client_id": "MOCK_ID", "access_token": "MOCK_TOKEN"}

    def save_config(self, config):
        self.config = config
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)

    def get_broker(self):
        if not self.broker:
            mode = self.config.get("mode", "paper")
            if mode == "live":
                client_id = self.config.get("client_id")
                access_token = self.config.get("access_token")
                self.broker = DhanProvider(client_id, access_token)
                if not self.broker.login():
                    self.logger.warning("Live login failed, falling back to Paper.")
                    self.broker = PaperBroker()
            else:
                self.broker = PaperBroker()
        return self.broker

    def ensure_logged_in(self):
        """
        Periodically checks if the session is still active.
        """
        if self.broker and hasattr(self.broker, 'login'):
            return self.broker.login()
        return True

    def automate_login(self):
        totp_secret = self.config.get("totp_secret")
        if totp_secret:
            totp = pyotp.TOTP(totp_secret)
            return totp.now()
        return None
