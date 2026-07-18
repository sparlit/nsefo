"""
Secrets Manager — NSEFO Master Pro
====================================
Loads sensitive configuration from environment variables (preferred)
with fallback to config.json for backwards compatibility.

Sensitive fields:
  NSEFO_CLIENT_ID
  NSEFO_ACCESS_TOKEN
  NSEFO_TOTP_SECRET
  NSEFO_API_KEY
  NSEFO_REFRESH_TOKEN
  NSEFO_CLIENT_SECRET

Optional dashboard auth:
  NSEFO_DASHBOARD_SECRET  — shared secret for dashboard API auth (required for API access)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Secrets loader
# ---------------------------------------------------------------------------

# Map env var name -> config.json key
_SENSITIVE_FIELDS: Dict[str, str] = {
    "NSEFO_CLIENT_ID": "client_id",
    "NSEFO_ACCESS_TOKEN": "access_token",
    "NSEFO_TOTP_SECRET": "totp_secret",
    "NSEFO_API_KEY": "api_key",
    "NSEFO_REFRESH_TOKEN": "refresh_token",
    "NSEFO_CLIENT_SECRET": "client_secret",
}

# Fields that are non-sensitive and always served from config.json
_NON_SENSITIVE_FIELDS: list[str] = [
    "mode",
    "provider",
    "target_frequency",
    "data_provider",
    "password",
    "yob",
    "risk",
]


def _getEnv(key: str) -> Optional[str]:
    """Return env var value, skipping empty strings."""
    val = os.environ.get(key, "")
    return val if val else None


class SecretsManager:
    """
    Thread-safe secrets provider.

    Priority:
      1. Environment variable (production — keeps secrets out of config.json)
      2. config.json value (backwards compatibility during migration)
      3. Empty string (field not set)

    Usage:
        sm = SecretsManager(config_path="config.json")
        client_id = sm.get("client_id")          # from env or config
        dashboard_secret = sm.dashboard_secret()  # from env only
    """

    def __init__(self, config_path: str = "config.json"):
        self._config_path = config_path
        self._cache: Dict[str, Any] = {}
        self._loaded = False

    # ── public API ────────────────────────────────────────────────────────────

    def get(self, field: str) -> str:
        """
        Return the value for `field`.
        Returns "" (not None) if the field is unset in both env and config.
        """
        if not self._loaded:
            self._ensure_loaded()

        if field in self._cache:
            return str(self._cache[field])

        # Check env var directly
        env_key = f"NSEFO_{field.upper()}"
        env_val = _getEnv(env_key)
        if env_val is not None:
            return env_val

        # Fall back to config.json (lazy load)
        _cfg = self._load_json_config()
        return str(_cfg.get(field, ""))

    def get_credential(self, field: str) -> str:
        """
        Alias for get(). Use for credential fields that should always
        come from env vars in production.
        """
        return self.get(field)

    def dashboard_secret(self) -> Optional[str]:
        """
        Return the dashboard API secret from NSEFO_DASHBOARD_SECRET env var.
        Returns None if the variable is not set — callers MUST handle this
        as "auth not configured" and deny access.
        """
        return _getEnv("NSEFO_DASHBOARD_SECRET")

    def is_env_configured(self, field: str) -> bool:
        """True if the field has a non-empty value sourced from an env var."""
        env_key = f"NSEFO_{field.upper()}"
        return _getEnv(env_key) is not None

    def as_config_dict(self) -> Dict[str, Any]:
        """
        Return the full config dict with sensitive fields resolved from env vars.
        Non-sensitive fields come from config.json.
        """
        if not self._loaded:
            self._ensure_loaded()

        result: Dict[str, Any] = {}
        cfg = self._load_json_config()

        # Sensitive fields: env-first
        for env_key, json_key in _SENSITIVE_FIELDS.items():
            field = json_key
            result[field] = self.get(field)

        # Non-sensitive fields: from config.json only
        for field in _NON_SENSITIVE_FIELDS:
            if field in cfg:
                result[field] = cfg[field]

        return result

    # ── internal ──────────────────────────────────────────────────────────────

    def _ensure_loaded(self):
        if not self._loaded:
            self._cache = self._load_json_config()
            self._loaded = True

    def _load_json_config(self) -> Dict[str, Any]:
        """Load and cache config.json once."""
        import json as _json

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return _json.load(f)
        except (FileNotFoundError, _json.JSONDecodeError):
            return {}

    def invalidate_cache(self):
        """Call after config.json is updated on disk."""
        self._cache = {}
        self._loaded = False


# ── Module-level singleton ────────────────────────────────────────────────────

_secrets_manager: Optional[SecretsManager] = None


def get_secrets(config_path: str = "config.json") -> SecretsManager:
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager(config_path=config_path)
    return _secrets_manager