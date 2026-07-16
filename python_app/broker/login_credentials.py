"""
Login credentials dataclass — standardizes Broker.login() signature.

Before: broker.login(api_key="", access_token="", client_id="", ...)  # kwargs
After:  broker.login(credentials=LoginCredentials(...))
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class LoginCredentials:
    """
    Immutable credentials container for broker authentication.

    Usage:
        creds = LoginCredentials(
            client_id="...",
            access_token="...",
            api_key="...",
            totp_secret="...",    # optional TOTP 2FA
            refresh_token="...",  # optional OAuth refresh
            client_secret="...",  # optional OAuth
            password="...",        # optional (Geojit form POST)
            yob="...",            # optional (Geojit year-of-birth)
        )
        broker.login(credentials=creds)
    """
    client_id: str = ""
    access_token: str = ""
    api_key: str = ""
    totp_secret: str = ""
    refresh_token: str = ""
    client_secret: str = ""
    password: str = ""
    yob: str = ""
    # Provider-specific extra fields as needed
    extra: Optional[dict] = None

    def has_totp(self) -> bool:
        return bool(self.totp_secret)

    @classmethod
    def from_dict(cls, data: dict) -> "LoginCredentials":
        """Build from a dict (e.g. from session_manager.config)."""
        return cls(
            client_id=data.get("client_id", ""),
            access_token=data.get("access_token", ""),
            api_key=data.get("api_key", ""),
            totp_secret=data.get("totp_secret", ""),
            refresh_token=data.get("refresh_token", ""),
            client_secret=data.get("client_secret", ""),
            password=data.get("password", ""),
            yob=data.get("yob", ""),
        )