"""
Per-broker configuration management.

BrokerConfig loads, validates, and persists per-broker settings
that are stored in config.json under the `_broker_config` key.
"""

import json, copy, os
from typing import Dict, Any, Optional


class BrokerConfig:
    """
    Per-broker configuration.

    Loads from config.json['_broker_config'][provider_key] and
    provides validation + defaults per provider.
    """

    DEFAULTS = {
        "verify_ssl": True,
        "timeout": 30,
        "paper_mode": True,
        "data_provider": "",
        "max_retries": 3,
        "retry_delay": 5,
        "log_level": "INFO",
    }

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

    def get(self, provider_key: str, key: str, default: Any = None) -> Any:
        """Get a config value for a specific broker."""
        broker_cfg = self._config.get('_broker_config', {}).get(provider_key, {})
        return broker_cfg.get(key, self.DEFAULTS.get(key, default))

    def set(self, provider_key: str, key: str, value: Any):
        """Set a config value for a specific broker."""
        if '_broker_config' not in self._config:
            self._config['_broker_config'] = {}
        if provider_key not in self._config['_broker_config']:
            self._config['_broker_config'][provider_key] = {}
        self._config['_broker_config'][provider_key][key] = value
        self._save_raw(self._config)

    def get_broker_config(self, provider_key: str) -> Dict[str, Any]:
        """Get full config dict for a broker (defaults merged)."""
        defaults = copy.deepcopy(self.DEFAULTS)
        saved = self._config.get('_broker_config', {}).get(provider_key, {})
        defaults.update(saved)
        return defaults

    def set_broker_config(self, provider_key: str, config: Dict[str, Any]):
        """Set the full config dict for a broker."""
        if '_broker_config' not in self._config:
            self._config['_broker_config'] = {}
        self._config['_broker_config'][provider_key] = config
        self._save_raw(self._config)

    def list_providers(self) -> list:
        """List all providers that have saved config."""
        return list(self._config.get('_broker_config', {}).keys())

    def is_activated(self, provider_key: str) -> bool:
        """Check if a broker has been activated (credentials + config)."""
        broker_cfg = self._config.get('_broker_config', {}).get(provider_key, {})
        return broker_cfg.get('activated', False)

    def mark_activated(self, provider_key: str, activated: bool = True):
        """Mark a broker as activated."""
        self.set(provider_key, 'activated', activated)

    def is_paper_mode(self, provider_key: str) -> bool:
        """Returns True if paper trading is enabled for this broker."""
        return self.get(provider_key, 'paper_mode', True)

    def get_data_provider(self, provider_key: str) -> str:
        """Returns the data provider used for real market data in paper mode."""
        return self.get(provider_key, 'data_provider', '')

    def validate_credentials(self, provider_key: str, creds: Dict[str, str]) -> bool:
        """
        Validate that required credentials are present and non-empty.
        Returns True if all required credentials are provided.
        """
        from .registry import PROVIDER_INFO
        info = PROVIDER_INFO.get(provider_key, {})
        required = info.get('required_credentials', [])
        missing = [c for c in required if not creds.get(c, '').strip()]
        return len(missing) == 0