"""
Broker Integration Configuration
=================================
Centralized, self-contained module for broker provider configuration.

Provides:
    PROVIDER_REGISTRY  — provider key → class mapping (26 live + 1 paper)
    BrokerFactory      — instantiates brokers from config; replaces
                         session_manager.py's if-elif chain
    BrokerConfig       — per-broker extended settings (verify_ssl, timeout,
                         max_retries, paper_mode, etc.)
    ProviderInfo       — broker metadata lookup (segments, auth_type,
                         required_credentials)
    DatabaseManager    — SQLite-backed broker database: metadata, encrypted
                         credentials, named config snapshots, usage stats
    BrokerImporter    — import from NSE registry, JSON, CSV, ProviderInfo,
                         or Python dicts; supports dry-run and merge strategies

Architecture
------------
python_app/broker/          ← working broker implementations (singular)
python_app/brokers/         ← NSE registry metadata system (plural, stubs)
python_app/broker_integration/  ← configuration & factory layer + database
"""

from .factory import BrokerFactory, ProviderInfo, PROVIDER_REGISTRY
from .config import BrokerConfig
from .database import DatabaseManager
from .importer import BrokerImporter, MergeStrategy

__all__ = [
    # Factory
    "BrokerFactory",
    "ProviderInfo",
    "PROVIDER_REGISTRY",
    # Config
    "BrokerConfig",
    # Database
    "DatabaseManager",
    # Importer
    "BrokerImporter",
    "MergeStrategy",
]