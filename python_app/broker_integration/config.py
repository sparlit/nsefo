"""
Per-broker extended configuration
===================================
Manages settings that live in config.json under the `_broker_config` key,
separate from the core credentials in the top-level config dict.

Settings include:
    verify_ssl    — SSL verification (default True)
    timeout       — HTTP request timeout in seconds (default 30)
    paper_mode    — Force paper mode for this broker regardless of global mode
    data_provider — Which broker to use for market data in paper mode
    max_retries   — Number of retries on transient HTTP failures (default 3)
    retry_delay   — Seconds between retries (default 5)
    log_level     — Per-broker log level: DEBUG|INFO|WARNING|ERROR

Usage
-----
    from python_app.broker_integration import BrokerConfig, ProviderInfo

    cfg = BrokerConfig()

    # Get a setting with defaults applied
    timeout = cfg.get(provider_key, "timeout", default=30)

    # Set a setting
    cfg.set(provider_key, "verify_ssl", False)

    # Get full config dict (defaults merged)
    broker_cfg = cfg.get_broker_config("zerodha")

    # Validate credentials against ProviderInfo metadata
    ok, missing = cfg.validate_credentials("dhan", {"client_id": "X", "access_token": "Y"})

    # Check if a broker has been activated (credentials confirmed working)
    if cfg.is_activated("zerodha"):
        print("Zerodha is ready to trade")
"""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .factory import ProviderInfo

logger = logging.getLogger(__name__)


class BrokerConfig:
    """
    Per-broker extended settings store.

    Backed by config.json['_broker_config'][provider_key].  Creates the
    key path automatically on first write.

    Defaults are defined in DEFAULTS and applied on read via
    get() / get_broker_config() — never stored in config.json unless
    explicitly overridden.
    """

    # Defaults applied to every broker that doesn't override them.
    DEFAULTS: Dict[str, Any] = {
        "verify_ssl": True,
        "timeout": 30,
        "paper_mode": True,
        "data_provider": "",
        "max_retries": 3,
        "retry_delay": 5.0,
        "log_level": "INFO",
    }

    def __init__(self, config_path: str = "config.json"):
        from pathlib import Path
        self.config_path = Path(config_path).resolve()
        self._raw: Dict[str, Any] = self._load()
        self._dirty = False

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load %s: %s", self.config_path, e)
        return {}

    def _save(self):
        """Write _raw back to config.json.  Called automatically on mutation."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._raw, f, indent=2)
            self._dirty = False
        except OSError as e:
            logger.error("Failed to persist %s: %s", self.config_path, e)

    def _broker_cfg(self, provider_key: str, create: bool = False) -> Dict[str, Any]:
        """Return (creating if needed) the dict for provider_key."""
        if "_broker_config" not in self._raw:
            if not create:
                return {}
            self._raw["_broker_config"] = {}
        pc = self._raw["_broker_config"]
        if provider_key not in pc:
            if not create:
                return {}
            pc[provider_key] = {}
        return pc[provider_key]

    # ------------------------------------------------------------------
    # Read / Write individual keys
    # ------------------------------------------------------------------

    def get(self, provider_key: str, key: str, default: Any = None) -> Any:
        """
        Get a single config value for provider_key.

        Falls back to DEFAULTS[key] if not set in config.json.
        """
        broker_cfg = self._broker_cfg(provider_key)
        if key in broker_cfg:
            return broker_cfg[key]
        return self.DEFAULTS.get(key, default)

    def set(self, provider_key: str, key: str, value: Any):
        """
        Set a single config value for provider_key.
        Persists to config.json immediately.
        """
        bc = self._broker_cfg(provider_key, create=True)
        bc[key] = value
        self._dirty = True
        self._save()

    # ------------------------------------------------------------------
    # Full config dict (with defaults merged)
    # ------------------------------------------------------------------

    def get_broker_config(self, provider_key: str) -> Dict[str, Any]:
        """
        Return full config for provider_key with DEFAULTS merged in.

        Does not mutate the stored config — overrides are only applied
        in the returned dict.
        """
        defaults = copy.deepcopy(self.DEFAULTS)
        saved = self._broker_cfg(provider_key)
        defaults.update(saved)
        return defaults

    def set_broker_config(self, provider_key: str, config: Dict[str, Any]):
        """
        Replace the entire stored config for provider_key.

        Keys not present in config retain their current stored values.
        To clear a key, set it to None (it will fall back to DEFAULTS on read).
        """
        bc = self._broker_cfg(provider_key, create=True)
        for k, v in config.items():
            if v is None:
                bc.pop(k, None)
            else:
                bc[k] = v
        self._dirty = True
        self._save()

    def reset_broker_config(self, provider_key: str):
        """
        Remove all stored config for provider_key, reverting to DEFAULTS.
        """
        pc = self._raw.get("_broker_config", {})
        if provider_key in pc:
            del pc[provider_key]
            self._dirty = True
            self._save()

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def list_providers(self) -> List[str]:
        """Return provider keys that have stored (non-default) config."""
        return list(self._raw.get("_broker_config", {}).keys())

    def is_activated(self, provider_key: str) -> bool:
        """True if the broker has been marked as activated (credentials verified)."""
        return bool(self._broker_cfg(provider_key).get("activated", False))

    def mark_activated(self, provider_key: str, activated: bool = True):
        """Mark or unmark a broker as activated."""
        self.set(provider_key, "activated", activated)

    def is_paper_mode(self, provider_key: str) -> bool:
        """True if paper_mode is forced for this broker (overrides global mode)."""
        return self.get(provider_key, "paper_mode", True)

    def get_data_provider(self, provider_key: str) -> str:
        """
        Return the provider key to use for market data in paper mode.
        Empty string means use the live broker itself.
        """
        return self.get(provider_key, "data_provider", "")

    def get_timeout(self, provider_key: str) -> float:
        """Return the HTTP timeout in seconds for this broker."""
        return float(self.get(provider_key, "timeout", 30))

    def get_max_retries(self, provider_key: str) -> int:
        """Return max retry count for transient failures."""
        return int(self.get(provider_key, "max_retries", 3))

    def get_retry_delay(self, provider_key: str) -> float:
        """Return seconds between retries."""
        return float(self.get(provider_key, "retry_delay", 5.0))

    # ------------------------------------------------------------------
    # Credential validation
    # ------------------------------------------------------------------

    def validate_credentials(
        self, provider_key: str, creds: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """
        Check whether creds contains all required fields for provider_key.

        Returns (is_valid, missing_fields).
        """
        info = ProviderInfo.get(provider_key)
        if info is None:
            logger.warning("Unknown provider_key %r in validate_credentials", provider_key)
            return True, []

        missing = [f for f in info.required_credentials if not creds.get(f, "").strip()]
        return len(missing) == 0, missing

    def validate_from_config(self, provider_key: str, config: dict) -> Tuple[bool, List[str]]:
        """
        Validate the credentials present in a config dict for provider_key.

        Convenience wrapper around validate_credentials() that extracts
        the relevant fields.
        """
        info = ProviderInfo.get(provider_key)
        if info is None:
            return True, []

        creds = {f: config.get(f, "") for f in info.required_credentials}
        return self.validate_credentials(provider_key, creds)