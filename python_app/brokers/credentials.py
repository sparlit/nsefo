"""
Credential management for brokers.

CredentialsManager stores broker credentials securely (encrypted at rest).
Uses Fernet (cryptography.fernet) for AES encryption if available,
otherwise falls back to base64 obfuscation with a warning.

Credentials are stored in config.json under `_broker_credentials[provider_key]`.
"""

import json, os, base64
from typing import Dict, Optional

try:
    from cryptography.fernet import Fernet
    _HAS_FERNET = True
except ImportError:
    _HAS_FERNET = False


class CredentialsManager:
    """
    Secure credential storage with AES encryption.

    Usage:
        cm = CredentialsManager()
        cm.save("zerodha", {"api_key": "...", "access_token": "..."})
        creds = cm.load("zerodha")  # returns decrypted dict
    """

    _KEY_ENV = "NSEFO_CREDENTIALS_KEY"
    _CONFIG_KEY = "_broker_credentials"

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._config = self._load_raw()
        self._fernet = self._get_fernet()

    def _load_raw(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_raw(self, cfg: dict):
        with open(self.config_path, 'w') as f:
            json.dump(cfg, f, indent=2)

    def _get_fernet(self):
        if not _HAS_FERNET:
            return None
        key = os.environ.get(self._KEY_ENV)
        if not key:
            raise RuntimeError(
                f"NSEFO_CREDENTIALS_KEY environment variable is not set. "
                f"Set it to a Fernet-compatible 32-byte base64-encoded key. "
                f"Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return Fernet(key.encode())

    def _encrypt(self, data: str) -> str:
        if self._fernet:
            return self._fernet.encrypt(data.encode()).decode()
        raise RuntimeError("cryptography package is not installed — cannot encrypt credentials")

    def _decrypt(self, token: str) -> str:
        if self._fernet:
            return self._fernet.decrypt(token.encode()).decode()
        raise RuntimeError("cryptography package is not installed — cannot decrypt credentials")

    def save(self, provider_key: str, credentials: Dict[str, str]):
        """
        Encrypt and save credentials for a provider.
        Only saves non-empty values.
        """
        if self._CONFIG_KEY not in self._config:
            self._config[self._CONFIG_KEY] = {}

        # Encrypt each credential value
        encrypted = {}
        for k, v in credentials.items():
            if v and isinstance(v, str) and v.strip():
                encrypted[k] = self._encrypt(v.strip())

        self._config[self._CONFIG_KEY][provider_key] = encrypted
        self._save_raw(self._config)

    def load(self, provider_key: str) -> Dict[str, str]:
        """
        Load and decrypt credentials for a provider.
        Returns empty dict if no credentials saved.
        """
        provider_creds = self._config.get(self._CONFIG_KEY, {}).get(provider_key, {})
        decrypted = {}
        for k, v in provider_creds.items():
            try:
                decrypted[k] = self._decrypt(v)
            except Exception:
                decrypted[k] = v  # fallback: try as plain text
        return decrypted

    def has_credentials(self, provider_key: str) -> bool:
        """Check if credentials exist for a provider."""
        creds = self._config.get(self._CONFIG_KEY, {}).get(provider_key, {})
        return len(creds) > 0

    def delete(self, provider_key: str):
        """Remove credentials for a provider."""
        if self._CONFIG_KEY in self._config:
            self._config[self._CONFIG_KEY].pop(provider_key, None)
            self._save_raw(self._config)

    def list_providers(self) -> list:
        """List all providers with saved credentials."""
        return list(self._config.get(self._CONFIG_KEY, {}).keys())

    def rotate(self, provider_key: str, new_credentials: Dict[str, str]):
        """Replace credentials (used after token refresh)."""
        self.save(provider_key, new_credentials)