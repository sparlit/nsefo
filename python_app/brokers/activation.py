"""
Broker activation management.

BrokerActivation tracks which brokers have been:
  1. Configured (BASE_URL + auth params set)
  2. Activated (login verified and working)

Activation state is stored in config.json under `_broker_activation`.
"""

import json, os, time
from typing import Dict, Optional


class BrokerActivation:
    """
    Tracks broker activation state.

    States:
      never_configured  — no credentials saved
      configured        — credentials saved but never activated
      activating        — login in progress
      active            — login verified, working
      expired           — token expired, needs re-auth
      error             — login failed
    """

    STATES = ['never_configured', 'configured', 'activating', 'active', 'expired', 'error']

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._config = self._load_raw()

    def _load_raw(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_raw(self, cfg: dict):
        with open(self.config_path, 'w') as f:
            json.dump(cfg, f, indent=2)

    def _activation_key(self, provider_key: str) -> str:
        return f"_broker_activation.{provider_key}"

    def get_state(self, provider_key: str) -> str:
        """Get current activation state for a provider."""
        return self._config.get(self._activation_key(provider_key), {}).get(
            'state', 'never_configured')

    def set_state(self, provider_key: str, state: str, details: str = ""):
        """Update activation state."""
        if state not in self.STATES:
            raise ValueError(f"Invalid state: {state}. Must be one of {self.STATES}")
        key = self._activation_key(provider_key)
        if key not in self._config:
            self._config[key] = {}
        self._config[key]['state'] = state
        self._config[key]['updated_at'] = time.time()
        if details:
            self._config[key]['details'] = details
        self._save_raw(self._config)

    def is_active(self, provider_key: str) -> bool:
        return self.get_state(provider_key) == 'active'

    def mark_active(self, provider_key: str):
        self.set_state(provider_key, 'active')

    def mark_error(self, provider_key: str, details: str = ""):
        self.set_state(provider_key, 'error', details)

    def mark_expired(self, provider_key: str):
        self.set_state(provider_key, 'expired')

    def mark_configured(self, provider_key: str):
        """Mark as configured (credentials saved but not yet activated)."""
        self.set_state(provider_key, 'configured')

    def reset(self, provider_key: str):
        """Reset activation state to configured (credentials still saved)."""
        self.set_state(provider_key, 'configured')

    def get_info(self, provider_key: str) -> Dict:
        """Get full activation info for a provider."""
        return self._config.get(self._activation_key(provider_key), {})

    def list_active(self) -> list:
        """List all providers in 'active' state."""
        return [
            pk for pk in
            (self._config.get('_broker_activation', {}) or {}).keys()
            if self.get_state(pk) == 'active'
        ]