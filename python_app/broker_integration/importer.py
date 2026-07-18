"""
Broker configuration importer
==============================
Import broker data from multiple sources into the broker database:

1. NSE Registry (`python_app/brokers/registry.py`) — 1000+ NSE-registered members
2. ProviderInfo (`python_app/broker_integration.factory`) — 26 live + 5 deprecated
3. JSON files — user-provided broker config exports
4. CSV files  — bulk import from spreadsheet exports

Usage
-----
    from python_app.broker_integration import BrokerImporter, DatabaseManager

    db  = DatabaseManager("brokers.db")
    imp = BrokerImporter(db)

    # Import all NSE registry brokers (1000+ entries)
    result = imp.from_nse_registry()
    print(f"Imported {result['imported']} of {result['total']} entries")

    # Import from built-in ProviderInfo (26 live providers)
    result = imp.from_provider_info()
    print(f"Imported {result['imported']} providers")

    # Import from a JSON backup
    result = imp.from_json_file("brokers_backup.json")
    print(f"Imported {result['brokers_imported']} brokers, "
          f"{result['configs_imported']} configs")

    # Import from CSV
    result = imp.from_csv("my_brokers.csv")
    print(f"Imported {result['imported']} of {result['total']} rows")

    # Import from a dict
    result = imp.from_dict({
        "provider_key": "my_broker",
        "name": "My Broker Ltd",
        "nse_code": "99999",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://api.mybroker.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
    })

    # Dry run (validate without writing)
    result = imp.from_nse_registry(dry_run=True)
    print("Would import:", result['would_import'])

    # Custom merge strategy
    result = imp.from_nse_registry(strategy="replace")  # overwrite existing
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .database import DatabaseManager
from .factory import ProviderInfo

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Merge strategies
# ------------------------------------------------------------------

class MergeStrategy:
    SKIP     = "skip"      # Don't overwrite existing records
    REPLACE  = "replace"   # Always insert (overwrite)
    MERGE    = "merge"     # Merge dicts, prefer non-empty new values


# ------------------------------------------------------------------
# Validation helpers
# ------------------------------------------------------------------

_VALID_API_STATUSES   = {"verified", "stub", "deprecated", "unknown", "bank", "individual"}
_VALID_AUTH_TYPES     = {"bearer", "apikey", "oauth2", "form", "totp", "unknown"}
_VALID_SEGMENTS       = {"CM", "F&O", "CD", "CO"}


def _validate_broker(data: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate a broker dict and return (is_valid, error_messages).

    strict=True: ALL fields must be present and valid.
    strict=False: only provider_key and name are required.
    """
    errors: List[str] = []
    pk = data.get("provider_key", "")

    if not pk:
        errors.append("provider_key is required")
    if not data.get("name"):
        errors.append("name is required")

    if strict:
        api_status = data.get("api_status", "")
        if api_status not in _VALID_API_STATUSES:
            errors.append(f"api_status must be one of {_VALID_API_STATUSES}, got {api_status!r}")

        auth_type = data.get("auth_type", "")
        if auth_type not in _VALID_AUTH_TYPES:
            errors.append(f"auth_type must be one of {_VALID_AUTH_TYPES}, got {auth_type!r}")

        segments = data.get("segments", [])
        if not isinstance(segments, list):
            errors.append(f"segments must be a list, got {type(segments).__name__}")
        else:
            invalid = [s for s in segments if s not in _VALID_SEGMENTS]
            if invalid:
                errors.append(f"invalid segments: {invalid} — valid: {_VALID_SEGMENTS}")

        creds = data.get("required_credentials", [])
        if not isinstance(creds, list):
            errors.append(f"required_credentials must be a list, got {type(creds).__name__}")

    return len(errors) == 0, errors


def _coerce_broker(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and coerce a broker dict to canonical form.

    Handles:
    - provider_key: strip whitespace, lowercase
    - segments: list of strings
    - required_credentials: list of strings
    - has_implementation: bool
    - deprecated: bool
    - api_status: lowercase stripped
    """
    pk = data.get("provider_key", "")
    if isinstance(pk, str):
        pk = pk.strip().lower().replace(" ", "_").replace("-", "_")
    else:
        pk = str(pk).strip().lower()

    name = data.get("name", "")
    if not isinstance(name, str):
        name = str(name)

    segments = data.get("segments", [])
    if isinstance(segments, str):
        # Handle comma or pipe separated
        segments = [s.strip() for s in segments.replace(",", "|").split("|") if s.strip()]
    segments = [str(s) for s in segments]

    required_credentials = data.get("required_credentials", [])
    if isinstance(required_credentials, str):
        required_credentials = [c.strip() for c in required_credentials.split(",") if c.strip()]
    required_credentials = [str(c) for c in required_credentials]

    return {
        "provider_key": pk,
        "name": name,
        "nse_code": str(data.get("nse_code", "") or ""),
        "segments": segments,
        "api_status": str(data.get("api_status", "unknown")).lower().strip(),
        "base_url": str(data.get("base_url", "") or ""),
        "auth_type": str(data.get("auth_type", "unknown")).lower().strip(),
        "required_credentials": required_credentials,
        "has_implementation": bool(data.get("has_implementation", False)),
        "deprecated": bool(data.get("deprecated", False)),
    }


# ------------------------------------------------------------------
# BrokerImporter
# ------------------------------------------------------------------

class BrokerImporter:
    """
    Import broker data from various sources into the broker database.

    All import methods return a result dict:
        {
            "total":     int,   -- total records considered
            "imported":  int,   -- records successfully imported
            "skipped":   int,   -- records skipped (existing, invalid, etc.)
            "errors":    list,  -- error messages for failed records
            "would_import": list, -- (dry_run only) dicts that would be imported
        }
    """

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()
        self._last_result: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Source: NSE Registry (python_app/brokers/registry.py)
    # ------------------------------------------------------------------

    def from_nse_registry(
        self,
        strategy: str = MergeStrategy.SKIP,
        dry_run: bool = False,
        api_status_filter: str = None,
    ) -> Dict[str, Any]:
        """
        Import all brokers from python_app.brokers.registry.PROVIDER_INFO.

        api_status_filter: if set, only import entries matching this status
                           (e.g. "verified" to only get live brokers)
        """
        from python_app.brokers.registry import PROVIDER_INFO

        total = 0
        imported = 0
        skipped = 0
        errors: List[str] = []
        would_import: List[Dict] = []

        for pk, info in PROVIDER_INFO.items():
            total += 1

            if api_status_filter and info.get("api_status") != api_status_filter:
                continue

            data = _coerce_broker(dict(info, provider_key=pk))
            data["has_implementation"] = "_implementation" in info
            # Remove internal key that shouldn't be stored
            data.pop("_implementation", None)

            valid, errs = _validate_broker(data)
            if not valid:
                errors.append(f"{pk}: {errs}")
                skipped += 1
                continue

            if dry_run:
                would_import.append(data)
                imported += 1
                continue

            existing = self.db.get_broker(pk)
            if existing and strategy == MergeStrategy.SKIP:
                skipped += 1
                continue

            try:
                self.db.upsert_broker(data, source="nse_registry")
                imported += 1
            except Exception as e:
                errors.append(f"{pk}: {e}")
                skipped += 1

        result = dict(total=total, imported=imported, skipped=skipped, errors=errors)
        if dry_run:
            result["would_import"] = would_import
        self._last_result = result
        return result

    # ------------------------------------------------------------------
    # Source: ProviderInfo (factory.py — 26 live + 5 deprecated)
    # ------------------------------------------------------------------

    def from_provider_info(
        self,
        strategy: str = MergeStrategy.SKIP,
        include_deprecated: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Import all registered ProviderInfo records from factory.py.

        These are the 26 brokers with active implementations plus 5 deprecated.
        """
        total = 0
        imported = 0
        skipped = 0
        errors: List[str] = []
        would_import: List[Dict] = []

        for pk in ProviderInfo.all_keys():
            info = ProviderInfo.get(pk)
            total += 1

            if info.deprecated and not include_deprecated:
                continue

            data = {
                "provider_key": pk,
                "name": info.name,
                "nse_code": info.nse_code,
                "segments": info.segments,
                "api_status": info.api_status,
                "base_url": info.base_url,
                "auth_type": info.auth_type,
                "required_credentials": info.required_credentials,
                "has_implementation": pk in _LIVE_PROVIDER_KEYS,
                "deprecated": info.deprecated,
            }

            valid, errs = _validate_broker(data)
            if not valid:
                errors.append(f"{pk}: {errs}")
                skipped += 1
                continue

            if dry_run:
                would_import.append(data)
                imported += 1
                continue

            existing = self.db.get_broker(pk)
            if existing and strategy == MergeStrategy.SKIP:
                skipped += 1
                continue

            try:
                self.db.upsert_broker(data, source="provider_info")
                imported += 1
            except Exception as e:
                errors.append(f"{pk}: {e}")
                skipped += 1

        result = dict(total=total, imported=imported, skipped=skipped, errors=errors)
        if dry_run:
            result["would_import"] = would_import
        self._last_result = result
        return result

    # ------------------------------------------------------------------
    # Source: JSON file
    # ------------------------------------------------------------------

    def from_json_file(
        self,
        path: str,
        strategy: str = MergeStrategy.SKIP,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Import brokers from a JSON file.

        Supports two formats:
          1. Export format: {"brokers": [...], "saved_configs": [...]}
          2. Simple list:  [{"provider_key": ..., "name": ...}, ...]
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"JSON file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Format 1: export format
        if isinstance(data, dict):
            brokers_imported, configs_imported = 0, 0
            if dry_run:
                # Validate brokers that would be imported
                imported = 0
                for b in data.get("brokers", []):
                    existing = self.db.get_broker(b.get("provider_key", ""))
                    if existing and strategy == MergeStrategy.SKIP:
                        continue
                    imported += 1
                result = dict(
                    total=len(data.get("brokers", [])),
                    imported=imported,
                    skipped=0,
                    errors=[],
                    brokers_imported=0,
                    configs_imported=0,
                )
            else:
                brokers_imported, configs_imported = self.db.import_from_json(data)
                result = dict(
                    total=len(data.get("brokers", [])),
                    imported=brokers_imported + configs_imported,
                    skipped=0,
                    errors=[],
                    brokers_imported=brokers_imported,
                    configs_imported=configs_imported,
                )
            self._last_result = result
            return result

        # Format 2: simple list
        if not isinstance(data, list):
            raise ValueError(
                f"JSON root must be a list or dict with 'brokers' key, "
                f"got {type(data).__name__}"
            )

        return self._from_dict_list(data, strategy=strategy, dry_run=dry_run)

    # ------------------------------------------------------------------
    # Source: CSV file
    # ------------------------------------------------------------------

    def from_csv(
        self,
        path: str,
        strategy: str = MergeStrategy.SKIP,
        dry_run: bool = False,
        required_columns: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Import brokers from a CSV file.

        required_columns: columns that MUST be present in the CSV header.
                         Defaults to ["provider_key", "name"].
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV file not found: {path}")

        required_columns = required_columns or ["provider_key", "name"]

        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Validate headers
        if not rows:
            return dict(total=0, imported=0, skipped=0, errors=["Empty CSV file"])

        missing_cols = [c for c in required_columns if c not in rows[0].keys()]
        if missing_cols:
            raise ValueError(
                f"CSV is missing required columns: {missing_cols}. "
                f"Found: {list(rows[0].keys())}"
            )

        # Parse each row
        brokers = []
        parse_errors: List[str] = []
        for i, row in enumerate(rows):
            try:
                # Convert CSV "1"/"0"/"true"/"false" strings to bool
                for bool_field in ("has_implementation", "deprecated"):
                    if bool_field in row:
                        v = str(row[bool_field]).strip().lower()
                        row[bool_field] = v in ("1", "true", "yes")

                # Handle JSON-in-CSV fields
                for json_field in ("segments", "required_credentials"):
                    if json_field in row and row[json_field]:
                        try:
                            row[json_field] = json.loads(row[json_field])
                        except json.JSONDecodeError:
                            # Try comma-separated
                            row[json_field] = [
                                x.strip() for x in row[json_field].split(",") if x.strip()
                            ]
                    else:
                        row[json_field] = []

                broker = _coerce_broker(dict(row))
                brokers.append(broker)
            except Exception as e:
                parse_errors.append(f"Row {i+2}: {e}")  # +2 for header + 1-indexed

        return self._from_dict_list(
            brokers,
            strategy=strategy,
            dry_run=dry_run,
            errors=parse_errors,
        )

    # ------------------------------------------------------------------
    # Source: Python dict / list of dicts
    # ------------------------------------------------------------------

    def from_dict(
        self,
        broker_data: Dict[str, Any],
        strategy: str = MergeStrategy.SKIP,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Import a single broker dict."""
        return self._from_dict_list([broker_data], strategy=strategy, dry_run=dry_run)

    def from_list(
        self,
        brokers: List[Dict[str, Any]],
        strategy: str = MergeStrategy.SKIP,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Import a list of broker dicts."""
        return self._from_dict_list(brokers, strategy=strategy, dry_run=dry_run)

    # ------------------------------------------------------------------
    # Common import helper
    # ------------------------------------------------------------------

    def _from_dict_list(
        self,
        brokers: List[Dict[str, Any]],
        strategy: str = MergeStrategy.SKIP,
        dry_run: bool = False,
        errors: List[str] = None,
    ) -> Dict[str, Any]:
        errors = list(errors) if errors else []
        imported = 0
        skipped = 0
        would_import: List[Dict] = []

        for b in brokers:
            data = _coerce_broker(b)
            valid, errs = _validate_broker(data)
            if not valid:
                errors.append(f"{data['provider_key']}: {errs}")
                skipped += 1
                continue

            if dry_run:
                would_import.append(data)
                imported += 1
                continue

            existing = self.db.get_broker(data["provider_key"])
            if existing:
                if strategy == MergeStrategy.SKIP:
                    skipped += 1
                    continue
                # strategy == REPLACE: overwrite
            try:
                self.db.upsert_broker(data, source="manual")
                imported += 1
            except Exception as e:
                errors.append(f"{data['provider_key']}: {e}")
                skipped += 1

        result = dict(
            total=len(brokers),
            imported=imported,
            skipped=skipped,
            errors=errors,
        )
        if dry_run:
            result["would_import"] = would_import
        self._last_result = result
        return result

    # ------------------------------------------------------------------
    # Convenience: populate full database from all sources
    # ------------------------------------------------------------------

    def populate_all(self, include_deprecated: bool = False) -> Dict[str, Any]:
        """
        Populate the database from all available sources.

        Order: NSE registry (bulk), then ProviderInfo (live overrides).

        This gives us:
        - 1000+ NSE-registered broker metadata
        - 26 live broker implementations override with confirmed base URLs/auth
        """
        results = {}

        # 1. NSE Registry (may have outdated base_url/auth for live brokers)
        r1 = self.from_nse_registry(strategy=MergeStrategy.SKIP)
        results["nse_registry"] = r1
        logger.info(
            "NSE registry: %d/%d imported, %d skipped, %d errors",
            r1["imported"], r1["total"], r1["skipped"], len(r1["errors"]),
        )

        # 2. ProviderInfo (live implementations — overrides registry data)
        r2 = self.from_provider_info(
            strategy=MergeStrategy.REPLACE,  # replace with confirmed data
            include_deprecated=include_deprecated,
        )
        results["provider_info"] = r2
        logger.info(
            "ProviderInfo: %d/%d imported, %d skipped, %d errors",
            r2["imported"], r2["total"], r2["skipped"], len(r2["errors"]),
        )

        return results

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def last_result(self) -> Dict[str, Any]:
        """Return the result of the most recent import."""
        return self._last_result

    @staticmethod
    def generate_csv_template(path: str = "brokers_import_template.csv"):
        """
        Write a CSV template to disk for bulk broker import.
        """
        fieldnames = [
            "provider_key", "name", "nse_code", "segments",
            "api_status", "base_url", "auth_type",
            "required_credentials", "has_implementation", "deprecated",
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "provider_key": "example_broker",
                "name": "Example Broker Ltd",
                "nse_code": "12345",
                "segments": '["F&O","CM"]',
                "api_status": "stub",
                "base_url": "https://api.example.com",
                "auth_type": "bearer",
                "required_credentials": '["client_id","access_token"]',
                "has_implementation": "0",
                "deprecated": "0",
            })
        logger.info("CSV template written to %s", path)


# Helper: set of live provider keys (those with real implementation files)
# This avoids a circular import; populated lazily
_LIVE_PROVIDER_KEYS: set = set()


def _populate_live_keys():
    global _LIVE_PROVIDER_KEYS
    try:
        from python_app.broker_integration.factory import PROVIDER_REGISTRY
        _LIVE_PROVIDER_KEYS = set(PROVIDER_REGISTRY.keys())
    except Exception as exc:
        import logging
        logging.warning("Could not populate live broker keys — registry may be incomplete: %s", exc)
        _LIVE_PROVIDER_KEYS = set()


_populate_live_keys()