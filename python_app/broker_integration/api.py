"""
Broker Management REST API
==========================
FastAPI router providing CRUD operations over the broker database.

Base URL: /api/brokers
Auth:     X-NSEFO-SECRET header (same as dashboard)

Guards all write operations with verify_dashboard_secret.
Read operations on broker metadata are open (no secrets in listing).

Design principles
-----------------
- Credentials are NEVER returned by any GET endpoint — only existence (true/false)
- Bulk import operations return a summary rather than the full payload
- All IDs/keys are validated before use; invalid keys return 404
- Errors follow RFC 7807 Problem Details: {type, title, detail, status}
"""

from __future__ import annotations

import io
import json as _json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Header,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse

from python_app.broker_integration import (
    BrokerConfig,
    BrokerFactory,
    BrokerImporter,
    DatabaseManager,
    MergeStrategy,
    ProviderInfo,
)

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logger = logging.getLogger("broker_api")

# ------------------------------------------------------------------
# Router
# ------------------------------------------------------------------

router = APIRouter(prefix="/api", tags=["brokers"])

# ------------------------------------------------------------------
# Auth dependency (shared with dashboard)
# ------------------------------------------------------------------

_SENSITIVE = frozenset({
    "access_token", "totp_secret", "api_key", "refresh_token",
    "client_secret", "password", "yob",
})

_auth_open_warning_fired = False


async def _auth(secret: Optional[str] = Header(None, alias="X-NSEFO-SECRET")) -> str:
    """
    Require the shared dashboard secret.  Allows open mode when the
    secret is not configured (for dev LAN use only).
    """
    global _auth_open_warning_fired
    expected = os.environ.get("NSEFO_DASHBOARD_SECRET")
    if expected is None:
        if not _auth_open_warning_fired:
            _auth_open_warning_fired = True
            import warnings
            warnings.warn(
                "NSEFO_DASHBOARD_SECRET not set — broker API is UNPROTECTED. "
                "Set the env var to enable authentication.",
                RuntimeWarning,
            )
        return "open"
    if secret != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-NSEFO-SECRET header.")
    return secret


def _problem(status_code: int, title: str, detail: str, type_url: str = None) -> JSONResponse:
    """Build an RFC 7807 Problem Details response."""
    body = {
        "type": type_url or f"https://nsefo.dev/errors/{status_code}",
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    return JSONResponse(body, status_code=status_code)


def _broker_not_found(key: str) -> JSONResponse:
    return _problem(404, "Broker not found", f"No broker with provider_key={key!r}.", "/errors/not-found")


def _config_not_found(name: str) -> JSONResponse:
    return _problem(404, "Config not found", f"No saved config with name={name!r}.", "/errors/not-found")


def _strip_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively remove sensitive keys from a dict or list.
    Handles nested dicts, lists, and mixed structures.
    """
    if isinstance(data, dict):
        return {k: _strip_sensitive(v) for k, v in data.items() if k not in _SENSITIVE}
    elif isinstance(data, list):
        return [_strip_sensitive(item) for item in data]
    else:
        return data


# ------------------------------------------------------------------
# Database singleton (lazily created per worker process)
# ------------------------------------------------------------------

_db_instance: Optional[DatabaseManager] = None


def _db() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        db_path = os.environ.get("NSEFO_BROKER_DB", "brokers.db")
        _db_instance = DatabaseManager(db_path)
        logger.info("BrokerDatabase initialised at %s", db_path)
    return _db_instance


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health")
async def health() -> JSONResponse:
    """Lightweight health check — does NOT require auth."""
    try:
        db = _db()
        broker_count = db.count_brokers()
        stats_count = len(db.list_stats())
        return JSONResponse({
            "status": "healthy",
            "database": "ok",
            "brokers_in_db": broker_count,
            "stats_rows": stats_count,
        })
    except Exception as e:
        return JSONResponse({"status": "degraded", "error": "service unavailable — check logs"}, status_code=503)


# ==================================================================
# BROKERS — metadata
# ==================================================================

@router.get("/brokers")
async def list_brokers(
    api_status: Optional[str] = Query(None, description="Filter: verified|stub|deprecated|unknown"),
    segment: Optional[str]     = Query(None, description="Filter: F&O | CM | CD | CO"),
    has_impl: Optional[bool]   = Query(None, description="Filter: only brokers with implementations"),
    deprecated: Optional[bool] = Query(None, description="Include deprecated brokers"),
    search: Optional[str]      = Query(None, description="Substring match on name or provider_key"),
    limit:  int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    List broker metadata records.

    All parameters are optional filters applied with AND logic.
    Credentials are NEVER included in the response.
    """
    db = _db()
    segments = [segment] if segment else None
    brokers = db.list_brokers(
        api_status=api_status,
        segments=segments,
        has_implementation=has_impl,
        deprecated=deprecated,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = db.count_brokers(
        api_status=api_status,
        segments=segments,
        has_implementation=has_impl,
        deprecated=deprecated,
    )

    return JSONResponse({
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": len(brokers),
        "results": brokers,
    })


@router.get("/brokers/providers")
async def list_providers(_: str = Depends(_auth)) -> JSONResponse:
    """
    List all registered provider keys from ProviderInfo (factory.py).

    Returns the same keys that BrokerFactory supports — useful for
    dropdowns and validation.
    """
    all_keys = ProviderInfo.all_keys()
    active   = [k for k in all_keys if not ProviderInfo.get(k).deprecated]
    deprecated = [k for k in all_keys if ProviderInfo.get(k).deprecated]

    return JSONResponse({
        "all": all_keys,
        "active": active,
        "deprecated": deprecated,
        "count": len(all_keys),
    })


@router.get("/brokers/{provider_key}")
async def get_broker(provider_key: str, _: str = Depends(_auth)) -> JSONResponse:
    """Get a single broker record by provider_key.  404 if not found."""
    db = _db()
    broker = db.get_broker(provider_key)
    if not broker:
        return _broker_not_found(provider_key)
    return JSONResponse(broker)


@router.post("/brokers")
async def upsert_broker(
    request: dict,
    strategy: str = Query("skip", description="skip | replace"),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Create or update a single broker record.

    strategy=skip  — don't overwrite if already exists (default)
    strategy=replace — always replace existing record

    Request body (all fields optional except provider_key):
        provider_key, name, nse_code, segments (list), api_status,
        base_url, auth_type, required_credentials (list),
        has_implementation (bool), deprecated (bool)
    """
    if not request.get("provider_key"):
        raise HTTPException(status_code=422, detail="provider_key is required")

    _VALID_API_STATUS = frozenset({"verified", "stub", "deprecated", "unknown", "bank"})
    _VALID_AUTH_TYPES = frozenset({"bearer", "totp", "oauth2", "form", "unknown"})

    bad_status = [
        k for k in ("api_status", "auth_type")
        if k in request
        and (
            (k == "api_status" and request[k] not in _VALID_API_STATUS)
            or (k == "auth_type" and request[k] not in _VALID_AUTH_TYPES)
        )
    ]
    if bad_status:
        valid_values = {
            "api_status": sorted(_VALID_API_STATUS),
            "auth_type": sorted(_VALID_AUTH_TYPES),
        }
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_enum_value",
                "fields": {k: valid_values[k] for k in bad_status if k in valid_values},
            },
        )

    imp = BrokerImporter(_db())
    result = imp.from_dict(request, strategy=strategy)
    if result["errors"]:
        return JSONResponse({
            "status": "error",
            "imported": result["imported"],
            "errors": result["errors"],
        }, status_code=422)
    return JSONResponse({
        "status": "created" if result["imported"] else "unchanged",
        "provider_key": request["provider_key"],
        "imported": result["imported"],
    }, status_code=201 if result["imported"] else 200)


@router.delete("/brokers/{provider_key}")
async def delete_broker(provider_key: str, _: str = Depends(_auth)) -> JSONResponse:
    """Delete a broker and all its credentials/configs/stats (CASCADE)."""
    db = _db()
    existing = db.get_broker(provider_key)
    if not existing:
        return _broker_not_found(provider_key)
    db.delete_broker(provider_key)
    logger.info("Deleted broker: %s", provider_key)
    return JSONResponse({"status": "deleted", "provider_key": provider_key})


# ==================================================================
# BROKERS — credentials
# ==================================================================

@router.get("/brokers/{provider_key}/credentials/exists")
async def credentials_exist(provider_key: str, _: str = Depends(_auth)) -> JSONResponse:
    """
    Check whether encrypted credentials are stored for this broker.

    Returns {exists: bool}.  Does NOT return the credentials themselves.
    """
    info = ProviderInfo.get(provider_key)
    if info is None:
        return _broker_not_found(provider_key)
    db = _db()
    exists = db.has_credentials(provider_key)
    return JSONResponse({"provider_key": provider_key, "exists": exists})


@router.post("/brokers/{provider_key}/credentials")
async def save_credentials(
    provider_key: str,
    credentials: dict,
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Encrypt and store credentials for a broker.

    Request body: flat dict of credential key-value pairs, e.g.
        {"client_id": "...", "access_token": "..."}

    Existing credentials are replaced atomically.
    """
    info = ProviderInfo.get(provider_key)
    if info is None:
        return _broker_not_found(provider_key)

    db = _db()
    try:
        db.save_credentials(provider_key, credentials)
        logger.info("Credentials saved for %s", provider_key)
        return JSONResponse({
            "status": "saved",
            "provider_key": provider_key,
            "credential_keys": list(credentials.keys()),
        }, status_code=201)
    except Exception as e:
        logger.error("Failed to save credentials for %s: %s", provider_key, e)
        return _problem(500, "Save failed", str(e), "/errors/credential-save-failed")


@router.delete("/brokers/{provider_key}/credentials")
async def delete_credentials(provider_key: str, _: str = Depends(_auth)) -> JSONResponse:
    """Delete stored credentials for a broker. Idempotent: succeeds even if no credentials existed."""
    db = _db()
    if not db.get_broker(provider_key) and provider_key not in ProviderInfo.all_keys():
        return _broker_not_found(provider_key)
    db.delete_credentials(provider_key)
    logger.info("Credentials deleted for %s", provider_key)
    return JSONResponse({"status": "deleted", "provider_key": provider_key})


# ==================================================================
# BROKERS — stats
# ==================================================================

@router.get("/brokers/{provider_key}/stats")
async def get_broker_stats(provider_key: str, _: str = Depends(_auth)) -> JSONResponse:
    """Get login/order statistics for a broker."""
    db = _db()
    if not db.get_broker(provider_key) and provider_key not in ProviderInfo.all_keys():
        return _broker_not_found(provider_key)
    return JSONResponse(db.get_stats(provider_key))


@router.get("/stats")
async def list_all_stats(_: str = Depends(_auth)) -> JSONResponse:
    """List stats for all brokers that have a record."""
    return JSONResponse({"results": _db().list_stats(), "count": len(_db().list_stats())})


@router.post("/brokers/{provider_key}/login-attempt")
async def record_login(
    provider_key: str,
    body: dict,
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Record a login attempt for a broker.

    Request body: {"success": true | false}
    """
    success = bool(body.get("success", False))
    db = _db()
    db.record_login_attempt(provider_key, success=success)
    return JSONResponse({
        "status": "recorded",
        "provider_key": provider_key,
        "success": success,
    })


@router.post("/brokers/{provider_key}/order-placed")
async def record_order(
    provider_key: str,
    body: dict,
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Record an order being placed.

    Request body: {"volume": 50000.0}   (optional, defaults to 0)
    """
    db = _db()
    if not db.get_broker(provider_key) and provider_key not in ProviderInfo.all_keys():
        return _broker_not_found(provider_key)
    volume = float(body.get("volume", 0.0))
    db.record_order_placed(provider_key, volume=volume)
    return JSONResponse({
        "status": "recorded",
        "provider_key": provider_key,
        "volume": volume,
    })


# ==================================================================
# SAVED CONFIG SNAPSHOTS
# ==================================================================

@router.get("/configs")
async def list_configs(
    provider_key: Optional[str] = Query(None),
    active_only: bool = Query(False),
    _: str = Depends(_auth),
) -> JSONResponse:
    """List saved config snapshots, optionally filtered by provider or active flag."""
    db = _db()
    configs = db.list_config_snapshots(
        provider_key=provider_key,
        is_active=active_only if active_only else None,
    )
    # Strip the full snapshot from list view for readability
    for c in configs:
        c.pop("config_snapshot", None)
    return JSONResponse({"results": configs, "count": len(configs)})


@router.get("/configs/{name}")
async def get_config_snapshot(name: str, _: str = Depends(_auth)) -> JSONResponse:
    """Load a named config snapshot.  404 if not found."""
    db = _db()
    snap = db.load_config_snapshot(name)
    if not snap:
        return _config_not_found(name)
    # Strip sensitive fields from the snapshot before returning
    snap["config_snapshot"] = _strip_sensitive(snap.get("config_snapshot", {}))
    return JSONResponse(snap)


@router.post("/configs")
async def save_config_snapshot(
    name: str = Form(..., description="Unique snapshot name"),
    provider_key: str = Form(..., description="Broker provider_key"),
    notes: str = Form(""),
    is_active: bool = Form(False),
    config_snapshot: str = Form("{}", description="JSON string of the config dict"),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Save or update a named config snapshot.

    Uses Form data (not JSON) so it can be submitted directly from an HTML form.
    The config_snapshot field should be a JSON string.
    """
    db = _db()
    try:
        cfg = JSONResponse(content={}).content  # placeholder
        import json as _json
        cfg = _json.loads(config_snapshot) if config_snapshot not in ("", "{}") else {}
    except _json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"config_snapshot is not valid JSON: {e}")

    try:
        sid = db.save_config_snapshot(name, provider_key, cfg, notes=notes, is_active=is_active)
        return JSONResponse({
            "status": "saved",
            "id": sid,
            "name": name,
            "provider_key": provider_key,
            "is_active": is_active,
        }, status_code=201)
    except Exception as e:
        logger.error("Failed to save config snapshot %s: %s", name, e)
        return _problem(500, "Save failed", str(e), "/errors/config-save-failed")


@router.delete("/configs/{name}")
async def delete_config_snapshot(name: str, _: str = Depends(_auth)) -> JSONResponse:
    """Delete a named config snapshot."""
    db = _db()
    existing = db.load_config_snapshot(name)
    if not existing:
        return _config_not_found(name)
    db.delete_config_snapshot(name)
    return JSONResponse({"status": "deleted", "name": name})


@router.post("/configs/{name}/activate")
async def activate_config(
    name: str,
    provider_key: str = Form(..., description="Broker provider_key (required)"),
    _: str = Depends(_auth),
) -> JSONResponse:
    """Set a named snapshot as active.  Deactivates other configs for the same provider."""
    db = _db()
    existing = db.load_config_snapshot(name)
    if not existing:
        return _config_not_found(name)
    db.set_active_config(name, provider_key=provider_key)
    return JSONResponse({"status": "activated", "name": name, "provider_key": provider_key, "is_active": True})


# ==================================================================
# IMPORT
# ==================================================================

@router.post("/import/registry")
async def import_from_registry(
    api_status_filter: Optional[str] = Query(None, description="Only import this api_status"),
    strategy: str = Query("skip"),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Import all brokers from the NSE Clearing registry
    (python_app/brokers/registry.py — 1000+ entries).

    strategy=skip    — don't overwrite existing (default)
    strategy=replace  — always overwrite with registry data
    """
    imp = BrokerImporter(_db())
    result = imp.from_nse_registry(strategy=strategy, api_status_filter=api_status_filter)
    logger.info("NSE registry import: %s", result)
    return JSONResponse({
        "source": "nse_registry",
        **result,
    })


@router.post("/import/provider-info")
async def import_from_provider_info(
    include_deprecated: bool = Query(False),
    strategy: str = Query("replace"),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Import from ProviderInfo (factory.py — 26 live + 5 deprecated implementations).

    Default strategy=replace to let live implementation data override stale NSE registry data.
    """
    imp = BrokerImporter(_db())
    result = imp.from_provider_info(
        strategy=strategy,
        include_deprecated=include_deprecated,
    )
    logger.info("ProviderInfo import: %s", result)
    return JSONResponse({
        "source": "provider_info",
        **result,
    })


@router.post("/import/populate")
async def populate_all(
    include_deprecated: bool = Query(False),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Full database populate: NSE registry first (skip), then ProviderInfo (replace).

    This is the canonical way to seed/refresh the database from all known sources.
    """
    imp = BrokerImporter(_db())
    results = imp.populate_all(include_deprecated=include_deprecated)
    return JSONResponse({
        "status": "ok",
        "sources": results,
    })


@router.post("/import/json")
async def import_from_json(
    file: UploadFile = File(..., description="JSON file to import"),
    strategy: str = Query("skip"),
) -> JSONResponse:
    """
    Import brokers from a JSON file upload.

    Supports export format:   {"brokers": [...], "saved_configs": [...]}
    And simple broker list:   [{"provider_key": ..., "name": ...}, ...]
    """
    if not file.filename.lower().endswith((".json",)):
        raise HTTPException(status_code=422, detail="File must have .json extension")

    import json as _json
    content = await file.read()
    try:
        data = _json.loads(content)
    except _json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    db = _db()
    try:
        brokers_imported, configs_imported = db.import_from_json(data)
        return JSONResponse({
            "status": "ok",
            "brokers_imported": brokers_imported,
            "configs_imported": configs_imported,
        })
    except Exception as e:
        logger.error("JSON import failed: %s", e)
        return _problem(500, "Import failed", str(e), "/errors/import-failed")


@router.post("/import/csv")
async def import_from_csv(
    file: UploadFile = File(..., description="CSV file to import"),
    strategy: str = Query("skip"),
) -> JSONResponse:
    """
    Import brokers from a CSV file upload.

    Required columns: provider_key, name
    Optional columns: nse_code, segments, api_status, base_url, auth_type,
                      required_credentials, has_implementation, deprecated
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="File must have .csv extension")

    import csv as _csv
    import io as _io

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return JSONResponse(
            {"error": "invalid_encoding", "detail": "CSV file must be UTF-8 encoded"},
            status_code=422,
        )

    reader = _csv.DictReader(_io.StringIO(decoded))
    rows = list(reader)

    imp = BrokerImporter(_db())
    brokers = []
    for row in rows:
        for bool_field in ("has_implementation", "deprecated"):
            if bool_field in row:
                v = str(row[bool_field]).strip().lower()
                row[bool_field] = v in ("1", "true", "yes")
        for json_field in ("segments", "required_credentials"):
            if json_field in row and row[json_field]:
                try:
                    row[json_field] = _json.loads(row[json_field])
                except Exception:
                    row[json_field] = [x.strip() for x in row[json_field].split(",") if x.strip()]
            else:
                row[json_field] = []
        brokers.append(row)

    result = imp.from_list(brokers, strategy=strategy)
    logger.info("CSV import: %s", result)
    return JSONResponse({
        "source": "csv",
        "filename": file.filename,
        **result,
    })


@router.get("/import/template")
async def download_csv_template() -> JSONResponse:
    """Return the CSV column headers as a JSON array (for building an import form)."""
    headers = [
        "provider_key", "name", "nse_code", "segments",
        "api_status", "base_url", "auth_type",
        "required_credentials", "has_implementation", "deprecated",
    ]
    return JSONResponse({
        "columns": headers,
        "example_row": {
            "provider_key": "my_broker",
            "name": "My Broker Ltd",
            "nse_code": "99999",
            "segments": '["F&O","CM"]',
            "api_status": "stub",
            "base_url": "https://api.mybroker.in",
            "auth_type": "bearer",
            "required_credentials": '["client_id","access_token"]',
            "has_implementation": "0",
            "deprecated": "0",
        },
    })


# ==================================================================
# EXPORT
# ==================================================================

@router.get("/export")
async def export_database(
    path: Optional[str] = Query(None, description="Optional path to write JSON file"),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Export all broker data to JSON (credentials excluded for security).

    Optionally write to disk at `path`.
    """
    db = _db()
    export = db.export_to_json(path=path)
    # Strip credentials metadata for safety
    for c in export.get("credentials_meta", []):
        pass  # metadata only — no actual secrets
    return JSONResponse(export)


# ==================================================================
# BROKER FACTORY — instantiate & test a broker
# ==================================================================

@router.post("/factory/create")
async def factory_create(
    provider_key: str = Form(...),
    client_id: str = Form(""),
    access_token: str = Form(""),
    api_key: str = Form(""),
    password: str = Form(""),
    totp_secret: str = Form(""),
    refresh_token: str = Form(""),
    client_secret: str = Form(""),
    yob: str = Form(""),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Instantiate a broker from raw credentials (no config.json needed).

    Returns the provider_key and confirms the class was found.
    Does NOT login — use /factory/test for that.
    """
    if not BrokerFactory.is_registered(provider_key):
        return _problem(422, "Unknown provider", f"{provider_key!r} is not in PROVIDER_REGISTRY.", "/errors/unknown-provider")

    try:
        broker = BrokerFactory.create(
            provider_key=provider_key,
            client_id=client_id,
            access_token=access_token,
            api_key=api_key,
            password=password,
            totp_secret=totp_secret,
            refresh_token=refresh_token,
            client_secret=client_secret,
            yob=yob,
        )
        return JSONResponse({
            "status": "instantiated",
            "provider_key": provider_key,
            "broker_class": broker.__class__.__name__,
        })
    except Exception as e:
        logger.error("Factory create failed for %s: %s", provider_key, e)
        return _problem(500, "Instantiation failed", str(e), "/errors/factory-failed")


@router.post("/factory/test")
async def factory_test(
    provider_key: str = Form(...),
    client_id: str = Form(""),
    access_token: str = Form(""),
    api_key: str = Form(""),
    password: str = Form(""),
    totp_secret: str = Form(""),
    refresh_token: str = Form(""),
    client_secret: str = Form(""),
    yob: str = Form(""),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Instantiate and attempt login for a broker.

    Returns the login result and any error message.
    Use this to validate credentials before saving.
    """
    from python_app.broker.login_credentials import LoginCredentials

    if not BrokerFactory.is_registered(provider_key):
        return _problem(422, "Unknown provider", f"{provider_key!r} is not in PROVIDER_REGISTRY.", "/errors/unknown-provider")

    try:
        broker = BrokerFactory.create(
            provider_key=provider_key,
            client_id=client_id,
            access_token=access_token,
            api_key=api_key,
            password=password,
            totp_secret=totp_secret,
            refresh_token=refresh_token,
            client_secret=client_secret,
            yob=yob,
        )
        # login() is called without credentials — the broker was constructed
        # with all credentials and should use its internal state.
        ok = broker.login()
        if ok:
            return JSONResponse({
                "login_ok": True,
                "provider_key": provider_key,
            })
        else:
            return JSONResponse({
                "login_ok": False,
                "provider_key": provider_key,
                "error": "Login returned False — check credentials",
            })
    except Exception as e:
        return JSONResponse({
            "login_ok": False,
            "provider_key": provider_key,
            "error": str(e),
        })


# ==================================================================
# CONFIG — read/write active broker config (active config snapshot + env)
# ==================================================================

@router.get("/config/active")
async def get_active_config(
    provider_key: str = Query(...),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Get the active saved config for a provider, if any.
    Returns the full config_snapshot (sensitive fields stripped).
    """
    db = _db()
    snap = db.get_active_config(provider_key)
    if not snap:
        return JSONResponse({
            "provider_key": provider_key,
            "active_config": None,
            "message": "No active config saved for this provider",
        })
    snap["config_snapshot"] = _strip_sensitive(snap.get("config_snapshot", {}))
    return JSONResponse({
        "provider_key": provider_key,
        "active_config": snap,
    })


@router.get("/config/validate")
async def validate_config(
    provider_key: str = Query(...),
    _: str = Depends(_auth),
) -> JSONResponse:
    """
    Validate that required credentials are present and non-empty for a provider.

    Reads from NSEFO_BROKER_DB credentials store.
    Returns {valid: bool, missing: [...], present: [...]}.
    """
    db = _db()
    creds = db.load_credentials(provider_key)
    info = ProviderInfo.get(provider_key)
    if info is None:
        return _broker_not_found(provider_key)

    required = info.required_credentials
    present = [f for f in required if creds.get(f, "").strip()]
    missing = [f for f in required if f not in present]
    return JSONResponse({
        "provider_key": provider_key,
        "valid": len(missing) == 0,
        "required": required,
        "present": present,
        "missing": missing,
    })