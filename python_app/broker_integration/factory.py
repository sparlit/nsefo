"""
BrokerFactory — centralized broker instantiation
===================================================
Replaces the if-elif chain in session_manager.get_broker() with a
registry-driven approach.  Add a new broker in one place: PROVIDER_REGISTRY.

Usage
-----
    from python_app.broker_integration import BrokerFactory, ProviderInfo

    # Instantiate a broker from the active config dict
    broker = BrokerFactory.from_config(config)

    # Instantiate a specific broker directly
    broker = BrokerFactory.create("zerodha", client_id="...", access_token="...")

    # Get broker metadata
    info = ProviderInfo.get("dhan")
    print(info.auth_type)   # "bearer"
    print(info.segments)   # ["F&O", "CM"]
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

if TYPE_CHECKING:
    from python_app.broker.base import Broker
    from python_app.broker.login_credentials import LoginCredentials

# ------------------------------------------------------------------
# Provider metadata
# ------------------------------------------------------------------

# Auth types used in ProviderInfo
AUTH_BEARER = "bearer"
AUTH_TOTP = "totp"
AUTH_OAUTH2 = "oauth2"
AUTH_FORM = "form"


class ProviderInfo:
    """
    Broker metadata record.  Used for UI display, credential validation,
    and documentation.  One record per provider key.
    """

    # Registry populated by _build_info() below
    _REGISTRY: Dict[str, "ProviderInfo"] = {}

    def __init__(
        self,
        key: str,
        name: str,
        nse_code: str = "",
        segments: list = None,
        api_status: str = "verified",
        base_url: str = "",
        auth_type: str = "bearer",
        required_credentials: list = None,
        deprecated: bool = False,
    ):
        self.key = key
        self.name = name
        self.nse_code = nse_code
        self.segments: list = segments or []
        self.api_status = api_status  # verified | stub | deprecated | unknown
        self.base_url = base_url
        self.auth_type = auth_type
        self.required_credentials: list = required_credentials or []
        self.deprecated = deprecated

    def __repr__(self):
        return f"<ProviderInfo[{self.key}] {self.name} ({self.api_status})>"

    @classmethod
    def register(cls, info: "ProviderInfo"):
        cls._REGISTRY[info.key] = info

    @classmethod
    def get(cls, key: str) -> Optional["ProviderInfo"]:
        return cls._REGISTRY.get(key)

    @classmethod
    def all_keys(cls) -> list:
        return list(cls._REGISTRY.keys())

    @classmethod
    def list_by_status(cls, api_status: str) -> list:
        return [k for k, v in cls._REGISTRY.items() if v.api_status == api_status]

    @classmethod
    def list_active(cls) -> list:
        return [k for k, v in cls._REGISTRY.items() if not v.deprecated]


def _build_info():
    """Populate ProviderInfo._REGISTRY.  Called at module load."""
    entries = [
        # key, name, nse_code, segments, auth_type, required_credentials
        ProviderInfo("dhan",       "Dhan",        "13908", ["F&O", "CM"], "verified", "https://api.dhan.com",          AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("fenix",      "Fenix Dhan",  "13908", ["F&O", "CM"], "verified", "https://api.dhan.com",          AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("zerodha",    "Zerodha",     "13906", ["F&O", "CM"], "verified", "https://api.kite.trade",        AUTH_BEARER,  ["api_key", "access_token"]),
        ProviderInfo("angelone",   "AngelOne",    "12798", ["F&O", "CM"], "verified", "https://apiv2.angelone.in",    AUTH_TOTP,    ["client_id", "password", "totp_secret"]),
        ProviderInfo("upstox",     "Upstox",      "13942", ["F&O", "CM"], "verified", "https://api.upstox.com",      AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("fyers",      "Fyers",       "13912", ["F&O", "CM"], "verified", "https://api.fyers.in",         AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("kotak",      "Kotak Securities", "08081", ["F&O", "CM"], "verified", "https://api.kotaksecurities.com", AUTH_BEARER, ["client_id", "access_token"]),
        ProviderInfo("kotak_neo",  "Kotak Neo",   "08081", ["F&O", "CM"], "stub",     "",                              AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("5paisa",     "5paisa",      "13918", ["F&O", "CM"], "verified", "https://opstrading.5paisa.com", AUTH_TOTP,    ["client_id", "password", "totp_secret"]),
        ProviderInfo("iifl",       "IIFL Markets","11805", ["F&O", "CM"], "verified", "https://api.iifl.in",          AUTH_BEARER,  ["api_key", "password"]),
        ProviderInfo("motilal",    "Motilal Oswal","13921", ["F&O", "CM"], "verified", "https://api.motilaloswal.com", AUTH_BEARER,  ["api_key", "password"]),
        ProviderInfo("finvasia",   "Finvasia",    "13920", ["F&O", "CM"], "verified", "https://api.shoonya.com",     AUTH_TOTP,    ["vendor_code", "yob", "totp_secret"]),
        ProviderInfo("aliceblue",  "AliceBlue",   "13902", ["F&O", "CM"], "verified", "https://api.aliceblue.com",   AUTH_BEARER,  ["app_code", "api_secret"]),
        ProviderInfo("choice",     "Choice Broking","13907", ["F&O", "CM"], "verified", "https://api.choiceindia.com", AUTH_BEARER,  ["client_id", "totp_secret"]),
        ProviderInfo("hdfc",       "HDFC Securities","11094",["F&O", "CM"], "verified", "https://api.hdfcsec.com",    AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("icici",      "ICICI Direct","13086", ["F&O", "CM"], "verified", "https://api.icicidirect.com",  AUTH_OAUTH2,  ["api_key", "client_secret", "access_token", "refresh_token"]),
        ProviderInfo("sbi",        "SBI Securities","13940",["F&O", "CM"], "verified", "https://www.sbismart.com",    AUTH_BEARER,  ["app_name", "access_token"]),
        ProviderInfo("bajaj",      "Bajaj Financial","14705",["F&O", "CM"], "verified", "https://api.bajajfinserv.com", AUTH_BEARER, ["api_key", "client_id", "access_token"]),
        ProviderInfo("geojit",      "Geojit",      "13910", ["F&O", "CM"], "verified", "https://api.geojit.com",       AUTH_FORM,    ["client_id", "password", "yob"]),
        ProviderInfo("sharekhan",  "Sharekhan",   "13925", ["F&O", "CM"], "verified", "https://api.sharekhan.com",   AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("anand_rathi","Anand Rathi", "13903", ["F&O", "CM"], "verified", "https://api.anandrathi.com",   AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("edelweiss",  "Edelweiss",   "13909", ["F&O", "CM"], "verified", "https://api.edelweiss.in",    AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("axis_direct","Axis Direct", "14816", ["F&O", "CM"], "verified", "https://api.axisdirect.in",   AUTH_BEARER,  ["client_id", "access_token"]),
        ProviderInfo("groww",      "Groww",       "13915", ["F&O", "CM"], "verified", "https://api.groww.in",        AUTH_BEARER,  ["api_key", "access_token"]),
        ProviderInfo("moneysukh",  "Moneysukh",   "13922", ["F&O", "CM"], "verified", "https://api.moneysukh.com",   AUTH_BEARER,  ["client_id", "api_key"]),
        ProviderInfo("master_trust","Master Trust","13919", ["F&O", "CM"], "verified", "https://api.mastertrust.com", AUTH_BEARER,  ["app_key"]),
        ProviderInfo("paper",      "PaperBroker", "",      ["F&O", "CM"], "verified", "",                               AUTH_BEARER,  []),
        # Deprecated — kept for reference
        ProviderInfo("vpc",        "VPC",         "",      ["F&O"],       "deprecated", "",  AUTH_BEARER, [], deprecated=True),
        ProviderInfo("nirmal_bang","Nirmal Bang", "",      ["F&O"],       "deprecated", "",  AUTH_BEARER, [], deprecated=True),
        ProviderInfo("kunjee",     "Kunjee",      "",      ["F&O"],       "deprecated", "",  AUTH_BEARER, [], deprecated=True),
        ProviderInfo("paytm_money", "Paytm Money", "",     ["CM"],        "deprecated", "",  AUTH_BEARER, [], deprecated=True),
        ProviderInfo("mstock",     "mStock",      "",      ["F&O"],       "deprecated", "",  AUTH_BEARER, [], deprecated=True),
    ]
    for e in entries:
        ProviderInfo.register(e)

_build_info()


# ------------------------------------------------------------------
# Broker class registry — one dict, no if-elif chain
# ------------------------------------------------------------------
# Each entry: provider_key → (BrokerClass, positional_args or None,
#                              kwarg_template_key_orNone)
#
# kwarg_template controls how config dict fields are passed to the
# constructor.  Three modes:
#   None         → class(client_id, access_token)  [most common]
#   "api_key"   → class(api_key=..., access_token=...)
#   "full"      → class(client_id=..., access_token=..., api_key=...,
#                        password=..., totp_secret=..., refresh_token=...,
#                        client_secret=..., yob=...)
#   "<custom>"  → class(**custom_kwargs)  [broker-specific]

_KWARG_MODE_NONE    = None
_KWARG_MODE_API_KEY = "api_key"
_KWARG_MODE_FULL    = "full"


class _ProviderEntry:
    __slots__ = ("cls", "arg_mode", "extra_config_keys")

    def __init__(self, cls, arg_mode=None, extra_config_keys=None):
        self.cls = cls
        self.arg_mode = arg_mode
        self.extra_config_keys = extra_config_keys or []


def _import_provider(module_path: str, class_name: str):
    """Lazy import helper — avoids importing all broker modules at startup."""
    import importlib
    mod = importlib.import_module(module_path, package="python_app.broker")
    return getattr(mod, class_name)


PROVIDER_REGISTRY: Dict[str, _ProviderEntry] = {
    # Dhan (SDK)
    "dhan": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".dhan", "DhanProvider")(client_id, access_token),
    ),
    # Fenix Dhan (primary)
    "fenix": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".fenix_broker", "FenixDhanProvider")(client_id, access_token),
    ),
    # Zerodha
    "zerodha": _ProviderEntry(
        lambda **kw: _import_provider(".zerodha", "ZerodhaProvider")(
            api_key=kw.get("api_key", ""), access_token=kw.get("access_token", "")
        ),
        arg_mode=_KWARG_MODE_API_KEY,
    ),
    # AngelOne
    "angelone": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".angelone", "AngelOneProvider")(client_id, access_token),
    ),
    # Upstox
    "upstox": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".upstox", "UpstoxProvider")(client_id, access_token),
    ),
    # Fyers
    "fyers": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".fyers", "FyersProvider")(client_id, access_token),
    ),
    # Kotak
    "kotak": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".kotak", "KotakProvider")(client_id, access_token),
    ),
    # Kotak Neo
    "kotak_neo": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".kotak_neo", "KotakNeoProvider")(client_id, access_token),
    ),
    # 5paisa
    "5paisa": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".fivepaisa", "FivePaisaProvider")(client_id, access_token),
    ),
    # IIFL
    "iifl": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".iifl", "IIFLProvider")(client_id, access_token),
    ),
    # Motilal
    "motilal": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".motilal", "MotilalProvider")(client_id, access_token),
    ),
    # Finvasia
    "finvasia": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".finvasia", "FinvasiaProvider")(client_id, access_token),
    ),
    # AliceBlue
    "aliceblue": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".aliceblue", "AliceBlueProvider")(client_id, access_token),
    ),
    # Choice
    "choice": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".choice", "ChoiceProvider")(client_id, access_token),
    ),
    # HDFC
    "hdfc": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".hdfc", "HDFCSecuritiesProvider")(client_id, access_token),
    ),
    # ICICI Direct (OAuth2 — needs all tokens)
    "icici": _ProviderEntry(
        lambda **kw: _import_provider(".icici", "ICICIDirectProvider")(
            client_id=kw.get("client_id", ""),
            api_key=kw.get("api_key", ""),
            access_token=kw.get("access_token", ""),
            refresh_token=kw.get("refresh_token", ""),
            client_secret=kw.get("client_secret", ""),
        ),
        arg_mode=_KWARG_MODE_FULL,
        extra_config_keys=["api_key", "refresh_token", "client_secret"],
    ),
    # SBI
    "sbi": _ProviderEntry(
        lambda **kw: _import_provider(".sbi", "SBISecuritiesProvider")(
            app_name=kw.get("client_id", ""), access_token=kw.get("access_token", "")
        ),
        arg_mode=_KWARG_MODE_FULL,
        extra_config_keys=["app_name"],
    ),
    # Bajaj
    "bajaj": _ProviderEntry(
        lambda **kw: _import_provider(".bajaj", "BajajFinancialProvider")(
            api_key=kw.get("api_key", ""),
            client_id=kw.get("client_id", ""),
            access_token=kw.get("access_token", ""),
        ),
        arg_mode=_KWARG_MODE_FULL,
        extra_config_keys=["api_key"],
    ),
    # Geojit (needs password + yob)
    "geojit": _ProviderEntry(
        lambda **kw: _import_provider(".geojit", "GeojitProvider")(
            client_id=kw.get("client_id", ""),
            password=kw.get("password", ""),
            yob=kw.get("yob", ""),
            access_token=kw.get("access_token", ""),
        ),
        arg_mode=_KWARG_MODE_FULL,
        extra_config_keys=["password", "yob"],
    ),
    # Sharekhan
    "sharekhan": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".sharekhan", "SharekhanProvider")(client_id, access_token),
    ),
    # Anand Rathi
    "anand_rathi": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".anand_rathi", "AnandRathiProvider")(client_id, access_token),
    ),
    # Edelweiss
    "edelweiss": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".edelweiss", "EdelweissProvider")(client_id, access_token),
    ),
    # Axis Direct
    "axis_direct": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".axis_direct", "AxisDirectProvider")(client_id, access_token),
    ),
    # Groww
    "groww": _ProviderEntry(
        lambda **kw: _import_provider(".groww", "GrowwProvider")(
            api_key=kw.get("api_key", ""), access_token=kw.get("access_token", "")
        ),
        arg_mode=_KWARG_MODE_API_KEY,
        extra_config_keys=["api_key"],
    ),
    # Moneysukh
    "moneysukh": _ProviderEntry(
        lambda **kw: _import_provider(".moneysukh", "MoneysukhProvider")(
            client_id=kw.get("client_id", ""),
            access_token=kw.get("access_token", ""),
            api_key=kw.get("api_key", ""),
        ),
        arg_mode=_KWARG_MODE_FULL,
        extra_config_keys=["api_key"],
    ),
    # Master Trust
    "master_trust": _ProviderEntry(
        lambda client_id, access_token, **kw: _import_provider(".master_trust", "MasterTrustProvider")(client_id, access_token),
    ),
}


# ------------------------------------------------------------------
# BrokerFactory
# ------------------------------------------------------------------

class BrokerFactory:
    """
    Factory for creating broker instances.

    Supports three instantiation modes:

    1. from_config(config: dict) → Broker
       Derives provider from config["provider"] and credentials from
       the same dict.  Handles all 26 live brokers + paper fallback.

    2. create(provider_key: str, client_id: str, access_token: str,
             *, api_key="", password="", totp_secret="",
             refresh_token="", client_secret="", yob="") → Broker
       Direct instantiation — no config dict needed.

    3. create_paper(data_provider: Broker = None) → PaperBroker
       Always returns a PaperBroker for simulation mode.
    """

    @staticmethod
    def create(
        provider_key: str,
        client_id: str = "",
        access_token: str = "",
        *,
        api_key: str = "",
        password: str = "",
        totp_secret: str = "",
        refresh_token: str = "",
        client_secret: str = "",
        yob: str = "",
    ) -> "Broker":
        """Instantiate a specific broker directly."""
        entry = PROVIDER_REGISTRY.get(provider_key)
        if entry is None:
            raise ValueError(
                f"Unknown provider_key {provider_key!r}. "
                f"Supported: {sorted(PROVIDER_REGISTRY.keys())}"
            )

        kw = dict(
            client_id=client_id,
            access_token=access_token,
            api_key=api_key,
            password=password,
            totp_secret=totp_secret,
            refresh_token=refresh_token,
            client_secret=client_secret,
            yob=yob,
        )
        return entry.cls(**kw)

    @staticmethod
    def create_paper(data_provider: "Broker" = None) -> "Broker":
        """Return a PaperBroker for simulation mode."""
        PaperBroker = _import_provider(".paper", "PaperBroker")
        return PaperBroker(data_provider=data_provider)

    @staticmethod
    def from_config(config: dict) -> "Broker":
        """
        Instantiate the broker described by a config dict.

        Returns (broker, actual_mode, mode_warning) — same three-value
        contract as the old session_manager.get_broker().
        """
        from python_app.broker.login_credentials import LoginCredentials

        mode = config.get("mode", "paper")
        provider_key = config.get("provider", "dhan")
        client_id = config.get("client_id", "")
        access_token = config.get("access_token", "")

        def _make_live():
            entry = PROVIDER_REGISTRY.get(provider_key)
            if entry is None:
                raise ValueError(
                    f"Unknown provider {provider_key!r}. "
                    f"Supported: {sorted(k for k in PROVIDER_REGISTRY if k != 'paper')}"
                )

            all_keys = dict(
                client_id=client_id,
                access_token=access_token,
                api_key=config.get("api_key", ""),
                password=config.get("password", ""),
                totp_secret=config.get("totp_secret", ""),
                refresh_token=config.get("refresh_token", ""),
                client_secret=config.get("client_secret", ""),
                yob=config.get("yob", ""),
            )
            return entry.cls(**all_keys)

        live_provider = _make_live()

        if mode == "live":
            creds = LoginCredentials.from_dict(config)
            if live_provider.login(credentials=creds):
                return live_provider, "live", ""
            # Silent paper fallback is dangerous — log critical
            import logging
            logging.getLogger("BrokerFactory").critical(
                "LIVE AUTH FAILED — Falling back to PaperBroker. "
                "Check credentials or switch to 'paper' mode."
            )
            return (
                BrokerFactory.create_paper(data_provider=live_provider),
                "paper",
                "LIVE AUTH FAILED — Running in PAPER mode. "
                "Check credentials or switch to 'paper' mode.",
            )
        else:
            return (
                BrokerFactory.create_paper(data_provider=live_provider),
                "paper",
                "",
            )

    @staticmethod
    def list_supported_providers() -> list:
        """Return list of all supported (non-deprecated) provider keys."""
        return [k for k in PROVIDER_REGISTRY if k != "paper"]

    @staticmethod
    def list_all_providers() -> list:
        """Return list of every provider key in the registry (incl. paper)."""
        return list(PROVIDER_REGISTRY.keys())

    @staticmethod
    def is_registered(provider_key: str) -> bool:
        return provider_key in PROVIDER_REGISTRY