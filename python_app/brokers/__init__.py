"""
NseFO Broker Module
-------------------
Dedicated module for all NSE-registered broker integrations.

Structure:
    brokers/
      __init__.py         — public API (get_broker, list_providers, etc.)
      base.py             — Broker ABC shared by all providers
      registry.py         — metadata for all 1100+ NSE member brokers
      config.py            — per-broker configuration management
      credentials.py        — credential storage (encrypted at rest)
      activation.py         — broker activation / license management
      providers/           — individual broker provider implementations
        __init__.py        — factory + all provider imports
        zerodha.py          full implementation
        upstox.py           full implementation
        ...                 (see providers/ dir)
"""

__version__ = "1.0.0"
__all__ = [
    "get_broker",
    "list_providers",
    "get_provider_info",
    "BrokerConfig",
    "CredentialsManager",
    "BrokerActivation",
    "BASE_PROVIDER_KEYS",
]

from .base import Broker
from .registry import (
    BASE_PROVIDER_KEYS,
    PROVIDER_INFO,
    get_broker,
    list_providers,
    get_provider_info,
)
from .config import BrokerConfig
from .credentials import CredentialsManager
from .activation import BrokerActivation