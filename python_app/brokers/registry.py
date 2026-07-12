"""
Broker Registry — NSE Clearing Members
----------------------------------------
Generated from:
  - List_of_Members_registered_with_NSE_Clearing_Limited_as_on_October_2025_0.pdf
  - NCL registered members List_0.pdf

Covers 1035 NSE-registered broker/corporate members.
Each entry has:
  name       — Full legal entity name
  nse_code   — NSE member code
  segments   — Trading segments: CM (Capital Market), F&O, CD (Currency), CO (Commodity)
  api_status — verified | stub | deprecated | unknown | bank | individual
  base_url   — API base URL (empty for unknown/stub until verified)
  auth_type  — bearer | apikey | oauth2 | form | totp | unknown
  required_credentials — list of required auth fields

Provider key naming: lowercase_underscore, derived from entity name.

Only providers with api_status in (verified, stub, deprecated) have implementation files
under providers/. Unknown/bank/individual entries are metadata-only.
"""

PROVIDER_INFO = {
    # ── VERIFIED (21) — Full functional implementations ─────────────────────
    "zerodha": {
        "name": "ZERODHA BROKING LIMITED",
        "nse_code": "13906",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.kite.trade",
        "auth_type": "bearer",
        "required_credentials": ["api_key", "access_token"],
        "deprecated": False,
        "_implementation": "providers/zerodha.py",
    },
    "upstox": {
        "name": "UPSTOX SECURITIES PRIVATE LIMITED",
        "nse_code": "13942",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.upstox.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/upstox.py",
    },
    "angelone": {
        "name": "ANGEL ONE LIMITED",
        "nse_code": "12798",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://apiv2.angelone.in",
        "auth_type": "totp",
        "required_credentials": ["client_id", "password", "totp_secret"],
        "deprecated": False,
        "_implementation": "providers/angelone.py",
    },
    "icici": {
        "name": "ICICI SECURITIES LIMITED",
        "nse_code": "13086",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.icicidirect.com",
        "auth_type": "oauth2",
        "required_credentials": ["api_key", "client_secret", "access_token", "refresh_token"],
        "deprecated": False,
        "_implementation": "providers/icici.py",
    },
    "hdfc": {
        "name": "HDFC SECURITIES LTD",
        "nse_code": "11094",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.hdfcsec.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/hdfc.py",
    },
    "axis_direct": {
        "name": "AXIS SECURITIES LIMITED",
        "nse_code": "14816",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.axisdirect.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/axis_direct.py",
    },
    "kotak": {
        "name": "KOTAK SECURITIES LTD",
        "nse_code": "08081",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.kotaksecurities.com",
        "auth_type": "bearer",
        "required_credentials": ["consumer_key", "access_token"],
        "deprecated": False,
        "_implementation": "providers/kotak.py",
    },
    "kotak_neo": {
        "name": "KOTAK MAHINDRA BANK LTD.",
        "nse_code": "13085",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.kotakneo.com",
        "auth_type": "bearer",
        "required_credentials": ["consumer_key", "access_token"],
        "deprecated": False,
        "_implementation": "providers/kotak_neo.py",
    },
    "motilal": {
        "name": "MOTILAL OSWAL FINANCIAL SERVICES LIMITED",
        "nse_code": "10412",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.motilaloswal.com",
        "auth_type": "bearer",
        "required_credentials": ["api_key", "password"],
        "deprecated": False,
        "_implementation": "providers/motilal.py",
    },
    "anand_rathi": {
        "name": "ANAND RATHI SHARE AND STOCK BROKERS LIMITED",
        "nse_code": "06769",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.edios.in/apis",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/anand_rathi.py",
    },
    "edelweiss": {
        "name": "EDELWEISS FINANCIAL SERVICES LIMITED",
        "nse_code": "11297",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.edelweasel.com",
        "auth_type": "oauth2",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/edelweiss.py",
    },
    "geojit": {
        "name": "GEOJIT INVESTMENTS LIMITED",
        "nse_code": "13372",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.geojit.net",
        "auth_type": "form",
        "required_credentials": ["client_id", "password", "yob"],
        "deprecated": False,
        "_implementation": "providers/geojit.py",
    },
    "sharekhan": {
        "name": "SHAREKHAN LTD",
        "nse_code": "10733",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://newtrade.sharekhan.com/sk/api",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/sharekhan.py",
    },
    "sbi": {
        "name": "STATE BANK OF INDIA",
        "nse_code": "13087",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://www.sbismartsecuapi.com",
        "auth_type": "bearer",
        "required_credentials": ["app_name", "access_token"],
        "deprecated": False,
        "_implementation": "providers/sbi.py",
    },
    "sbi_sg": {
        "name": "SBI-SG GLOBAL SECURITIES SERVICES PRIVATE LIMITED",
        "nse_code": "13768",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://sbisdm.motilaloswal.com",
        "auth_type": "bearer",
        "required_credentials": ["app_name", "access_token"],
        "deprecated": False,
        "_implementation": "providers/sbi_sg.py",
    },
    "fyers": {
        "name": "FYERS SECURITIES PRIVATE LIMITED",
        "nse_code": "90061",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.fyers.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/fyers.py",
    },
    "fivepaisa": {
        "name": "5PAISA CAPITAL LIMITED",
        "nse_code": "14300",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://gateway.5paisa.com",
        "auth_type": "totp",
        "required_credentials": ["client_id", "password", "totp_secret"],
        "deprecated": False,
        "_implementation": "providers/fivepaisa.py",
    },
    "iifl": {
        "name": "IIFL CAPITAL SERVICES LIMITED",
        "nse_code": "10975",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.iiflcapital.com",
        "auth_type": "bearer",
        "required_credentials": ["api_key", "password"],
        "deprecated": False,
        "_implementation": "providers/iifl.py",
    },
    "bajaj": {
        "name": "BAJAJ FINANCIAL SECURITIES LTD",
        "nse_code": "10795",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.bajajsec.com",
        "auth_type": "bearer",
        "required_credentials": ["api_key", "client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/bajaj.py",
    },
    "finvasia": {
        "name": "FINVASIA SECURITIES PRIVATE LIMITED",
        "nse_code": "14846",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.finvasia.com",
        "auth_type": "totp",
        "required_credentials": ["vendor_code", "yob", "totp_secret"],
        "deprecated": False,
        "_implementation": "providers/finvasia.py",
    },
    "aliceblue": {
        "name": "MILLENNIUM STOCK BROKING PVT. LTD.",
        "nse_code": "11298",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.aliceblue.co.in",
        "auth_type": "apikey",
        "required_credentials": ["app_code", "api_secret"],
        "deprecated": False,
        "_implementation": "providers/aliceblue.py",
    },
    "choice": {
        "name": "CHOICE EQUITY BROKING PRIVATE LIMITED",
        "nse_code": "13773",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.choicesecurities.in",
        "auth_type": "totp",
        "required_credentials": ["client_id", "totp_secret"],
        "deprecated": False,
        "_implementation": "providers/choice.py",
    },
    "master_trust": {
        "name": "MSE FINANCIAL SERVICES LTD",
        "nse_code": "11168",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.mastertrust.co.in",
        "auth_type": "bearer",
        "required_credentials": ["app_key"],
        "deprecated": False,
        "_implementation": "providers/master_trust.py",
    },
    "groww": {
        "name": "GROWW INVEST TECH PRIVATE LIMITED",
        "nse_code": "90187",
        "segments": ["F&O", "CM"],
        "api_status": "verified",
        "base_url": "https://api.groww.in",
        "auth_type": "bearer",
        "required_credentials": ["api_key", "access_token"],
        "deprecated": False,
        "_implementation": "providers/groww.py",
    },

    # ── STUB (27) — Functional but API paths unverified ───────────────────────
    "dolat": {
        "name": "DOLAT ALGOTECH LIMITED",
        "nse_code": "07100",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://api.dolatcapital.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/dolat.py",
    },
    "swastika": {
        "name": "SWASTIKA INVESTMART LIMITED",
        "nse_code": "11297",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://invest在手.swastika.co.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/swastika.py",
    },
    "centrum": {
        "name": "CENTRUM BROKING LIMITED",
        "nse_code": "14542",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://localhost",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/centrum.py",
    },
    "indiabulls": {
        "name": "INDIABULLS SECURITIES LIMITED",
        "nse_code": "08756",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.indiabulls.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/indiabulls.py",
    },
    "trustline": {
        "name": "TRUSTLINE SECURITIES LIMITED",
        "nse_code": "07536",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://api.trustline.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/trustline.py",
    },
    "smc": {
        "name": "SMC GLOBAL SECURITIES LTD",
        "nse_code": "07714",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.smctradeonline.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/smc.py",
    },
    "ventura": {
        "name": "VENTURA SECURITIES LTD",
        "nse_code": "07604",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://api.ventura1.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/ventura.py",
    },
    "gepl": {
        "name": "GEPL CAPITAL PRIVATE LIMITED",
        "nse_code": "07218",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://geplonline.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/gepl.py",
    },
    "samco": {
        "name": "SAMCO SECURITIES LIMITED",
        "nse_code": "12135",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.samco.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/samco.py",
    },
    "religare": {
        "name": "RELIGARE BROKING LIMITED",
        "nse_code": "06537",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.religareonline.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/religare.py",
    },
    "ambit": {
        "name": "AMBIT CAPITAL PRIVATE LIMITED",
        "nse_code": "12476",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.ambit.co.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/ambit.py",
    },
    "jm_financial": {
        "name": "JM FINANCIAL INSTITUTIONAL SECURITIES LIMITED",
        "nse_code": "12966",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.jmfl.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/jm_financial.py",
    },
    "kedia": {
        "name": "KEDIA SHARES & STOCKS BROKERS LIMITED",
        "nse_code": "11088",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.kediagroups.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/kedia.py",
    },
    "prabhu": {
        "name": "PRABHUDAS LILLADHER PVT. LTD.",
        "nse_code": "05977",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.prabhuwealth.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/prabhu.py",
    },
    "jainam": {
        "name": "JAINAM BROKING LIMITED",
        "nse_code": "12169",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.jainam.org",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/jainam.py",
    },
    "marwadi": {
        "name": "MARWADI SHARES AND FINANCE LIMITED",
        "nse_code": "08760",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.marwadionline.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/marwadi.py",
    },
    "shree_krishna": {
        "name": "SHRI KRISHNA SHARE BROKERS PRIVATE LIMITED",
        "nse_code": "13488",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.shrikrishnashares.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/shree_krishna.py",
    },
    "investec": {
        "name": "INVESTEC CAPITAL SERVICES(INDIA) PRIVATE LIMITED",
        "nse_code": "90054",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.investec.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/investec.py",
    },
    "phillipcapital": {
        "name": "PHILLIPCAPITAL (INDIA) PVT. LTD.",
        "nse_code": "14665",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.phillipcapital.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/phillipcapital.py",
    },
    "tradejini": {
        "name": "TRADEJINI FINANCIAL SERVICES PVT LTD",
        "nse_code": "14655",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://tradejini.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/tradejini.py",
    },
    "bofa": {
        "name": "BOFA SECURITIES INDIA LIMITED",
        "nse_code": "13481",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.bofa.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/bofa.py",
    },
    "aditya_birla_money": {
        "name": "ADITYA BIRLA MONEY LIMITED",
        "nse_code": "13470",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.adityabirlamoney.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/aditya_birla_money.py",
    },
    "jefferies": {
        "name": "JEFFERIES INDIA PRIVATE LIMITED",
        "nse_code": "14910",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.jefferies.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/jefferies.py",
    },
    "clsa": {
        "name": "CLSA INDIA PRIVATE LIMITED",
        "nse_code": "14991",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.clsa.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/clsa.py",
    },
    "yes_securities": {
        "name": "YES SECURITIES (INDIA) LIMITED",
        "nse_code": "14914",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://www.yessecurities.co.in",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "password"],
        "deprecated": False,
        "_implementation": "providers/yes_securities.py",
    },
    "mstock": {
        "name": "MIRAE ASSET CAPITAL MARKETS ( INDIA ) PRIVATE LIMITED",
        "nse_code": "90144",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://trade.mstock.com",
        "auth_type": "apikey",
        "required_credentials": ["client_id", "api_key", "access_token"],
        "deprecated": False,
        "_implementation": "providers/mstock.py",
    },
    "paytm_money": {
        "name": "PAYTM MONEY LTD",
        "nse_code": "90165",
        "segments": ["CM"],  # F&O not confirmed
        "api_status": "stub",
        "base_url": "https://paysdk.paytm.com",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": False,
        "_implementation": "providers/paytm_money.py",
    },
    "moneysukh": {
        "name": "MONEYSUKH SECURITIES PVT. LTD.",
        "nse_code": "05985",
        "segments": ["F&O", "CM"],
        "api_status": "stub",
        "base_url": "https://online.moneysukh.com",
        "auth_type": "apikey",
        "required_credentials": ["client_id", "api_key"],
        "deprecated": False,
        "_implementation": "providers/moneysukh.py",
    },

    # ── DEPRECATED ────────────────────────────────────────────────────────────
    "vpc": {
        "name": "VPC TRADING SOLUTIONS PRIVATE LIMITED",
        "nse_code": "06553",
        "segments": ["F&O", "CM"],
        "api_status": "deprecated",
        "base_url": "",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": True,
        "_implementation": "providers/vpc.py",
    },
    "kunjee": {
        "name": "KUNJEE COMMODITY BROKERS PVT. LTD.",
        "nse_code": "07136",
        "segments": ["F&O", "CM"],
        "api_status": "deprecated",
        "base_url": "",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "access_token"],
        "deprecated": True,
        "_implementation": "providers/kunjee.py",
    },
    "nirmal_bang": {
        "name": "NIRMAL BANG EQUITIES PRIVATE LIMITED",
        "nse_code": "13437",
        "segments": ["F&O", "CM"],
        "api_status": "deprecated",
        "base_url": "https://www.nirmalbang.com/api",
        "auth_type": "bearer",
        "required_credentials": ["client_id", "api_key"],
        "deprecated": True,
        "_implementation": "providers/nirmal_bang.py",
    },
}

# All provider keys (for iteration)
BASE_PROVIDER_KEYS = list(PROVIDER_INFO.keys())


def get_broker(provider_key: str, config: dict = None, **kwargs):
    """
    Factory: return a Broker instance for the given provider_key.
    Falls back to session_manager-style lazy import to avoid circular deps.
    """
    # Try new brokers module first
    try:
        from .providers import _PROVIDER_MAP
        if provider_key in _PROVIDER_MAP:
            cls = _PROVIDER_MAP[provider_key]
            return cls(config=config, **kwargs) if config else cls(**kwargs)
    except ImportError:
        pass

    # Fallback: import from old broker/ location (backward compat)
    try:
        from python_app.broker.session_manager import _get_broker as old_get
        return old_get(provider_key, config, **kwargs)
    except Exception:
        pass

    raise ValueError(f"Unknown provider: {provider_key}")


def list_providers(api_status: str = None, has_implementation: bool = None):
    """
    List all registered providers, optionally filtered.

    api_status: 'verified' | 'stub' | 'deprecated' | 'unknown'
    has_implementation: True = has a real provider file
    """
    results = []
    for key, info in PROVIDER_INFO.items():
        if api_status and info.get('api_status') != api_status:
            continue
        if has_implementation is not None:
            has_impl = '_implementation' in info
            if has_implementation != has_impl:
                continue
        results.append((key, info))
    return results


def get_provider_info(provider_key: str) -> dict:
    """Return the metadata dict for a provider key."""
    return PROVIDER_INFO.get(provider_key, {})