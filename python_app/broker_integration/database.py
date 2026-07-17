"""
SQLite database for broker configuration management
=====================================================
Stores broker metadata, encrypted credentials, named config snapshots,
and usage statistics in `brokers.db`.

Schema
------
brokers             — NSE clearing member registry (1035 entries)
broker_credentials  — AES-encrypted credentials per provider
saved_configs       — named complete config snapshots
broker_stats        — login success/failure counts, order counts

Usage
-----
    from python_app.broker_integration import DatabaseManager

    db = DatabaseManager("brokers.db")

    # List all verified F&O brokers
    for row in db.list_brokers(api_status="verified", segments=["F&O"]):
        print(row["provider_key"], row["name"])

    # Save a named config snapshot
    db.save_config_snapshot("my-paper-setup", "zerodha", {...}, notes="Testing")

    # Load a saved config
    cfg = db.load_config_snapshot("my-paper-setup")

    # Track a login attempt
    db.record_login_attempt("zerodha", success=True)

    # Encrypt and store credentials
    db.save_credentials("zerodha", {"api_key": "...", "access_token": "..."})
    creds = db.load_credentials("zerodha")   # decrypted

    # Export all data
    db.export_to_json("brokers_backup.json")
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS brokers (
    provider_key     TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    nse_code         TEXT,
    segments         TEXT NOT NULL DEFAULT '[]',   -- JSON list
    api_status       TEXT NOT NULL DEFAULT 'unknown',
    base_url         TEXT NOT NULL DEFAULT '',
    auth_type        TEXT NOT NULL DEFAULT 'unknown',
    required_credentials TEXT NOT NULL DEFAULT '[]', -- JSON list
    has_implementation INTEGER NOT NULL DEFAULT 0,
    deprecated       INTEGER NOT NULL DEFAULT 0,
    imported_at      TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'registry'  -- registry | provider_info | manual
);

CREATE TABLE IF NOT EXISTS broker_credentials (
    provider_key    TEXT PRIMARY KEY,
    encrypted_creds TEXT NOT NULL DEFAULT '{}',  -- JSON of encrypted fields
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    last_used_at    TEXT,
    FOREIGN KEY (provider_key) REFERENCES brokers(provider_key)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS saved_configs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    provider_key    TEXT NOT NULL,
    config_snapshot TEXT NOT NULL DEFAULT '{}',   -- JSON
    notes           TEXT NOT NULL DEFAULT '',
    is_active       INTEGER NOT NULL DEFAULT 0,   -- 1 = current active config
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (provider_key) REFERENCES brokers(provider_key)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS broker_stats (
    provider_key           TEXT PRIMARY KEY,
    login_success_count    INTEGER NOT NULL DEFAULT 0,
    login_failure_count    INTEGER NOT NULL DEFAULT 0,
    last_success_at        TEXT,
    last_failure_at        TEXT,
    total_orders_placed    INTEGER NOT NULL DEFAULT 0,
    last_order_at         TEXT,
    total_volume          REAL NOT NULL DEFAULT 0.0,
    updated_at             TEXT NOT NULL,
    FOREIGN KEY (provider_key) REFERENCES brokers(provider_key)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_brokers_status ON brokers(api_status);
CREATE INDEX IF NOT EXISTS idx_brokers_segments ON brokers(segments);
CREATE INDEX IF NOT EXISTS idx_configs_provider ON saved_configs(provider_key);
CREATE INDEX IF NOT EXISTS idx_configs_active  ON saved_configs(is_active);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _dict_to_json(col: dict) -> str:
    return json.dumps(col, ensure_ascii=False)


def _json_to_dict(raw: str) -> dict:
    try:
        return json.loads(raw) or {}
    except (json.JSONDecodeError, TypeError):
        return {}


# ------------------------------------------------------------------
# DatabaseManager
# ------------------------------------------------------------------

class DatabaseManager:
    """
    SQLite-backed broker configuration database.

    All write operations are wrapped in transactions and auto-commit.
    Credentials are encrypted using CredentialsManager before storage.
    """

    def __init__(self, db_path: str = "brokers.db"):
        self.db_path = db_path
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema migrations
    # ------------------------------------------------------------------

    SCHEMA_VERSION = 1

    def _ensure_schema(self):
        """Run base schema and apply any pending migrations via user_version."""
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            current = conn.execute("PRAGMA user_version").fetchone()[0]
            if current < self.SCHEMA_VERSION:
                conn.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
                conn.commit()
                logger.info(
                    "Broker database migrated from schema v%d → v%d",
                    current, self.SCHEMA_VERSION,
                )
            # Run any incremental migrations from current version
            if current < self.SCHEMA_VERSION:
                self._run_migrations(conn, current)
                conn.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
                conn.commit()

    def _run_migrations(self, conn: sqlite3.Connection, from_version: int):
        """Apply incremental schema changes. Safe to call multiple times (idempotent)."""
        if from_version < 1:
            # Schema v1 is the full schema in SCHEMA; no incremental ALTER needed.
            # Future migrations go here, e.g.:
            # if from_version < 2:
            #     conn.execute("ALTER TABLE brokers ADD COLUMN new_col TEXT")
            pass

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=30.0)

    def close(self):
        """Close any held connections. Idempotent."""
        # sqlite3.Connection doesn't have an explicit close needed
        # when used as context manager — called for API completeness
        pass

    # ------------------------------------------------------------------
    # Row helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_broker(row: sqlite3.Row) -> Dict[str, Any]:
        if row is None:
            return {}
        return {
            "provider_key": row["provider_key"],
            "name": row["name"],
            "nse_code": row["nse_code"],
            "segments": _json_to_dict(row["segments"]),
            "api_status": row["api_status"],
            "base_url": row["base_url"],
            "auth_type": row["auth_type"],
            "required_credentials": _json_to_dict(row["required_credentials"]),
            "has_implementation": bool(row["has_implementation"]),
            "deprecated": bool(row["deprecated"]),
            "imported_at": row["imported_at"],
            "source": row["source"],
        }

    # ------------------------------------------------------------------
    # brokers table
    # ------------------------------------------------------------------

    def upsert_broker(self, broker_data: Dict[str, Any], source: str = "manual"):
        """
        Insert or replace a broker record.

        broker_data keys: provider_key, name, nse_code, segments (list),
        api_status, base_url, auth_type, required_credentials (list),
        has_implementation, deprecated
        """
        now = _now()
        segs = broker_data.get("segments", [])
        req_creds = broker_data.get("required_credentials", [])
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO brokers
                    (provider_key, name, nse_code, segments, api_status,
                     base_url, auth_type, required_credentials,
                     has_implementation, deprecated, imported_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider_key) DO UPDATE SET
                    name               = excluded.name,
                    nse_code          = excluded.nse_code,
                    segments          = excluded.segments,
                    api_status        = excluded.api_status,
                    base_url          = excluded.base_url,
                    auth_type         = excluded.auth_type,
                    required_credentials = excluded.required_credentials,
                    has_implementation = excluded.has_implementation,
                    deprecated        = excluded.deprecated,
                    source            = excluded.source
                """,
                (
                    broker_data["provider_key"],
                    broker_data.get("name", ""),
                    broker_data.get("nse_code", ""),
                    _dict_to_json(segs) if isinstance(segs, list) else segs,
                    broker_data.get("api_status", "unknown"),
                    broker_data.get("base_url", ""),
                    broker_data.get("auth_type", "unknown"),
                    _dict_to_json(req_creds) if isinstance(req_creds, list) else req_creds,
                    int(bool(broker_data.get("has_implementation", False))),
                    int(bool(broker_data.get("deprecated", False))),
                    now,
                    source,
                ),
            )
            conn.commit()

    def upsert_brokers_batch(self, brokers: List[Dict[str, Any]], source: str = "registry"):
        """Bulk upsert — more efficient for large imports."""
        now = _now()
        rows = []
        for b in brokers:
            segs = b.get("segments", [])
            req_creds = b.get("required_credentials", [])
            rows.append((
                b["provider_key"],
                b.get("name", ""),
                b.get("nse_code", ""),
                _dict_to_json(segs) if isinstance(segs, list) else segs,
                b.get("api_status", "unknown"),
                b.get("base_url", ""),
                b.get("auth_type", "unknown"),
                _dict_to_json(req_creds) if isinstance(req_creds, list) else req_creds,
                int(bool(b.get("has_implementation", False))),
                int(bool(b.get("deprecated", False))),
                now,
                source,
            ))
        with self._conn() as conn:
            conn.executemany(
                """
                INSERT INTO brokers
                    (provider_key, name, nse_code, segments, api_status,
                     base_url, auth_type, required_credentials,
                     has_implementation, deprecated, imported_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider_key) DO UPDATE SET
                    name               = excluded.name,
                    nse_code          = excluded.nse_code,
                    segments          = excluded.segments,
                    api_status        = excluded.api_status,
                    base_url          = excluded.base_url,
                    auth_type         = excluded.auth_type,
                    required_credentials = excluded.required_credentials,
                    has_implementation = excluded.has_implementation,
                    deprecated        = excluded.deprecated,
                    source            = excluded.source
                """,
                rows,
            )
            conn.commit()

    def get_broker(self, provider_key: str) -> Dict[str, Any]:
        """Return one broker record, or empty dict if not found."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM brokers WHERE provider_key = ?", (provider_key,)
            ).fetchone()
            return self._row_to_broker(row) if row else {}

    def list_brokers(
        self,
        api_status: str = None,
        segments: List[str] = None,
        has_implementation: bool = None,
        deprecated: bool = None,
        search: str = None,
        limit: int = None,
        offset: int = None,
    ) -> List[Dict[str, Any]]:
        """
        List brokers with optional filters.

        segments: list of required segments (e.g. ["F&O"]). Broker must have
                  ALL listed segments to match.
        search:   case-insensitive substring match on name or provider_key
        """
        sql = "SELECT * FROM brokers WHERE 1=1"
        params: List[Any] = []

        if api_status:
            sql += " AND api_status = ?"
            params.append(api_status)

        if has_implementation is not None:
            sql += " AND has_implementation = ?"
            params.append(int(has_implementation))

        if deprecated is not None:
            sql += " AND deprecated = ?"
            params.append(int(deprecated))

        if segments:
            for seg in segments:
                sql += " AND segments LIKE ?"
                params.append(f"%{seg}%")

        if search:
            sql += " AND (name LIKE ? OR provider_key LIKE ?)"
            pat = f"%{search}%"
            params.extend([pat, pat])

        sql += " ORDER BY name"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
            if offset is not None:
                sql += " OFFSET ?"
                params.append(offset)

        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_broker(r) for r in rows]

    def delete_broker(self, provider_key: str):
        """Delete a broker and all its related data (CASCADE)."""
        with self._conn() as conn:
            conn.execute("DELETE FROM brokers WHERE provider_key = ?", (provider_key,))
            conn.commit()

    def count_brokers(self, **filters) -> int:
        """Count brokers matching the same filters as list_brokers()."""
        # Build a matching query manually since we want total count
        sql = "SELECT COUNT(*) FROM brokers WHERE 1=1"
        params: List[Any] = []

        if filters.get("api_status"):
            sql += " AND api_status = ?"
            params.append(filters["api_status"])
        if filters.get("has_implementation") is not None:
            sql += " AND has_implementation = ?"
            params.append(int(filters["has_implementation"]))
        if filters.get("segments"):
            for seg in filters["segments"]:
                sql += " AND segments LIKE ?"
                params.append(f"%{seg}%")
        if filters.get("deprecated") is not None:
            sql += " AND deprecated = ?"
            params.append(int(filters["deprecated"]))

        with self._conn() as conn:
            return conn.execute(sql, params).fetchone()[0]

    # ------------------------------------------------------------------
    # broker_credentials table
    # ------------------------------------------------------------------

    def save_credentials(self, provider_key: str, credentials: Dict[str, str]):
        """
        Encrypt and store credentials for a provider.

        Uses CredentialsManager for AES encryption and stores metadata in SQLite.
        Raises if encryption is unavailable (never stores plaintext).
        """
        from python_app.brokers.credentials import CredentialsManager
        cm = CredentialsManager()
        cm.save(provider_key, credentials)
        logger.info("Saved encrypted credentials for %s via CredentialsManager", provider_key)
        # CredentialsManager stores encrypted data in config.json.
        # SQLite holds only metadata (timestamps, no credential values).
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO broker_credentials
                    (provider_key, encrypted_creds, created_at, updated_at, last_used_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(provider_key) DO UPDATE SET
                    encrypted_creds = excluded.encrypted_creds,
                    updated_at       = excluded.updated_at
                """,
                (provider_key, "", now, now, now),
            )
            conn.commit()

    def load_credentials(self, provider_key: str) -> Dict[str, str]:
        """Load and decrypt credentials for a provider."""
        try:
            from python_app.brokers.credentials import CredentialsManager
            cm = CredentialsManager()
            creds = cm.load(provider_key)
            # Update last_used_at
            now = _now()
            with self._conn() as conn:
                conn.execute(
                    "UPDATE broker_credentials SET last_used_at = ? "
                    "WHERE provider_key = ?",
                    (now, provider_key),
                )
                conn.commit()
            return creds
        except Exception:
            # Fallback: try plain JSON
            with self._conn() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT encrypted_creds FROM broker_credentials WHERE provider_key = ?",
                    (provider_key,),
                ).fetchone()
            if row:
                try:
                    return json.loads(row["encrypted_creds"]) or {}
                except json.JSONDecodeError:
                    return {}
            return {}

    def has_credentials(self, provider_key: str) -> bool:
        """True if encrypted credentials exist for this provider."""
        try:
            from python_app.brokers.credentials import CredentialsManager
            cm = CredentialsManager()
            return cm.has_credentials(provider_key)
        except Exception:
            return False

    def delete_credentials(self, provider_key: str):
        """Remove stored credentials for a provider."""
        try:
            from python_app.brokers.credentials import CredentialsManager
            cm = CredentialsManager()
            cm.delete(provider_key)
        except Exception:
            pass
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM broker_credentials WHERE provider_key = ?",
                (provider_key,),
            )
            conn.commit()

    def list_providers_with_credentials(self) -> List[str]:
        """Return provider keys that have stored credentials."""
        try:
            from python_app.brokers.credentials import CredentialsManager
            cm = CredentialsManager()
            return cm.list_providers()
        except Exception:
            return []

    # ------------------------------------------------------------------
    # saved_configs table
    # ------------------------------------------------------------------

    def save_config_snapshot(
        self,
        name: str,
        provider_key: str,
        config_snapshot: Dict[str, Any],
        notes: str = "",
        is_active: bool = False,
    ) -> int:
        """
        Save or update a named config snapshot.

        Returns the row id.
        If is_active=True, deactivates all other configs for this provider.
        """
        now = _now()
        with self._conn() as conn:
            if is_active:
                conn.execute(
                    "UPDATE saved_configs SET is_active = 0 WHERE provider_key = ?",
                    (provider_key,),
                )
            conn.execute(
                """
                INSERT INTO saved_configs
                    (name, provider_key, config_snapshot, notes, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    provider_key    = excluded.provider_key,
                    config_snapshot = excluded.config_snapshot,
                    notes           = excluded.notes,
                    is_active       = excluded.is_active,
                    updated_at       = excluded.updated_at
                """,
                (name, provider_key, _dict_to_json(config_snapshot), notes, int(is_active), now, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM saved_configs WHERE name = ?", (name,)
            ).fetchone()
            return row[0] if row else -1

    def load_config_snapshot(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a named config snapshot, or None if not found."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM saved_configs WHERE name = ?", (name,)
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "provider_key": row["provider_key"],
            "config_snapshot": _json_to_dict(row["config_snapshot"]),
            "notes": row["notes"],
            "is_active": bool(row["is_active"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_config_snapshots(
        self,
        provider_key: str = None,
        is_active: bool = None,
    ) -> List[Dict[str, Any]]:
        """List config snapshots, optionally filtered."""
        sql = "SELECT * FROM saved_configs WHERE 1=1"
        params: List[Any] = []
        if provider_key:
            sql += " AND provider_key = ?"
            params.append(provider_key)
        if is_active is not None:
            sql += " AND is_active = ?"
            params.append(int(is_active))
        sql += " ORDER BY updated_at DESC"

        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "name": row["name"],
                    "provider_key": row["provider_key"],
                    "config_snapshot": _json_to_dict(row["config_snapshot"]),
                    "notes": row["notes"],
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })
            return result

    def get_active_config(self, provider_key: str) -> Optional[Dict[str, Any]]:
        """Return the active config for a provider, or None."""
        snapshot = self.list_config_snapshots(
            provider_key=provider_key, is_active=True
        )
        return snapshot[0] if snapshot else None

    def set_active_config(self, name: str, provider_key: str = None):
        """Set a named snapshot as active (deactivates others)."""
        with self._conn() as conn:
            # Deactivate all for this provider (or all if no provider_key)
            if provider_key:
                conn.execute(
                    "UPDATE saved_configs SET is_active = 0 WHERE provider_key = ?",
                    (provider_key,),
                )
            else:
                conn.execute("UPDATE saved_configs SET is_active = 0")
            # Activate the named one
            conn.execute(
                "UPDATE saved_configs SET is_active = 1 WHERE name = ?",
                (name,),
            )
            conn.commit()

    def delete_config_snapshot(self, name: str):
        """Delete a named config snapshot."""
        with self._conn() as conn:
            conn.execute("DELETE FROM saved_configs WHERE name = ?", (name,))
            conn.commit()

    # ------------------------------------------------------------------
    # broker_stats table
    # ------------------------------------------------------------------

    def record_login_attempt(self, provider_key: str, success: bool):
        """Record a login attempt for stats tracking."""
        now = _now()
        with self._conn() as conn:
            if success:
                conn.execute(
                    """
                    INSERT INTO broker_stats
                        (provider_key, login_success_count, last_success_at, updated_at)
                    VALUES (?, 1, ?, ?)
                    ON CONFLICT(provider_key) DO UPDATE SET
                        login_success_count = login_success_count + 1,
                        last_success_at     = excluded.last_success_at,
                        updated_at          = excluded.updated_at
                    """,
                    (provider_key, now, now),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO broker_stats
                        (provider_key, login_failure_count, last_failure_at, updated_at)
                    VALUES (?, 1, ?, ?)
                    ON CONFLICT(provider_key) DO UPDATE SET
                        login_failure_count = login_failure_count + 1,
                        last_failure_at      = excluded.last_failure_at,
                        updated_at           = excluded.updated_at
                    """,
                    (provider_key, now, now),
                )
            conn.commit()

    def record_order_placed(self, provider_key: str, volume: float = 0.0):
        """Increment order count and optionally volume."""
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO broker_stats
                    (provider_key, total_orders_placed, total_volume, last_order_at, updated_at)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(provider_key) DO UPDATE SET
                    total_orders_placed = total_orders_placed + 1,
                    total_volume         = total_volume + excluded.total_volume,
                    last_order_at        = excluded.last_order_at,
                    updated_at           = excluded.updated_at
                """,
                (provider_key, volume, now, now),
            )
            conn.commit()

    def get_stats(self, provider_key: str) -> Dict[str, Any]:
        """Return stats for a provider, or a zeroed record if none exist."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM broker_stats WHERE provider_key = ?",
                (provider_key,),
            ).fetchone()
        if not row:
            return {
                "provider_key": provider_key,
                "login_success_count": 0,
                "login_failure_count": 0,
                "last_success_at": None,
                "last_failure_at": None,
                "total_orders_placed": 0,
                "total_volume": 0.0,
                "last_order_at": None,
                "updated_at": None,
            }
        return dict(row)

    def list_stats(self) -> List[Dict[str, Any]]:
        """Return stats for all providers that have records."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM broker_stats ORDER BY login_failure_count DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_to_json(self, path: str = None) -> Dict[str, Any]:
        """
        Export all database data to a JSON dict (not including credentials).

        Optionally write to disk at `path`.
        """
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row

            brokers = [
                self._row_to_broker(r)
                for r in conn.execute("SELECT * FROM brokers").fetchall()
            ]

            # Omit encrypted_creds and all timestamps from export for security
            # (credential metadata like last_used_at reveals account usage patterns)
            creds_rows = conn.execute("SELECT provider_key FROM broker_credentials").fetchall()
            creds_meta = [{"provider_key": r["provider_key"]} for r in creds_rows]

            configs = self.list_config_snapshots()
            stats = self.list_stats()

        export = {
            "version": 1,
            "exported_at": _now(),
            "brokers": brokers,
            "credentials_meta": creds_meta,  # metadata only — no actual credentials
            "saved_configs": configs,
            "stats": stats,
        }

        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export, f, indent=2, ensure_ascii=False)
            logger.info("Exported %d brokers, %d configs to %s",
                        len(brokers), len(configs), path)

        return export

    def import_from_json(self, data: Dict[str, Any]) -> Tuple[int, int]:
        """
        Import brokers and configs from a JSON dict (as produced by export_to_json).

        Skips any provider_key that already exists (merge=skip).
        Returns (brokers_imported, configs_imported).
        """
        brokers_imported = 0
        configs_imported = 0

        # Import brokers
        for b in data.get("brokers", []):
            existing = self.get_broker(b["provider_key"])
            if existing:
                continue
            self.upsert_broker(b, source="import:json")
            brokers_imported += 1

        # Import saved configs
        for cfg in data.get("saved_configs", []):
            snapshot = cfg.get("config_snapshot", {})
            try:
                self.save_config_snapshot(
                    name=cfg["name"],
                    provider_key=cfg["provider_key"],
                    config_snapshot=snapshot,
                    notes=cfg.get("notes", ""),
                    is_active=bool(cfg.get("is_active")),
                )
                configs_imported += 1
            except Exception as e:
                logger.warning("Skipping config %r: %s", cfg.get("name"), e)

        return brokers_imported, configs_imported

    def clear_all_data(self):
        """Delete all data from all tables. Use with care."""
        with self._conn() as conn:
            conn.execute("DELETE FROM broker_stats")
            conn.execute("DELETE FROM saved_configs")
            conn.execute("DELETE FROM broker_credentials")
            conn.execute("DELETE FROM brokers")
            conn.commit()
        logger.warning("All broker database data cleared.")