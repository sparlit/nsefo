#!/usr/bin/env python3
"""
NSEFO Master Pro - Canonical Startup Entry Point
================================================
Single word commands:
  Windows : nsefo          (or: install.bat / setup.bat)
  Linux   : ./nsefo        (or: ./install / ./setup)

This is the ONLY entry point for starting the application.
All other .bat/.sh wrappers delegate here.

Usage:
  python run.py                        # Full GUI app
  python run.py --setup                # Re-run configuration wizard
  python run.py "Buy Nifty 24500 ce"   # Single NLP command, then exit
  python run.py --non-interactive     # Start without connectivity check
"""
import sys
import os

# ── Must be the first line — set PYTHONPATH before any imports ──────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")

# Load credentials from .env file (if present) before any app imports.
# Secrets in .env take priority over config.json values.
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT + os.sep + ".env")
except ImportError:
    pass   # python-dotenv not installed — credentials come from config.json or env vars only


# ── Stdlib imports ──────────────────────────────────────────────────────────
import json
import subprocess
import logging
import time
import threading

# ── Local imports ───────────────────────────────────────────────────────────
from python_app.broker.session_manager import SessionManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [STARTUP] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("startup")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def check_python_version():
    """Require Python 3.10+. Exit with clear message if not met."""
    if sys.version_info < (3, 10):
        logger.error("Python 3.10+ required. You have %s", sys.version.split()[0])
        logger.error("Download from: https://www.python.org/downloads/")
        sys.exit(1)
    logger.info("Python %s verified", sys.version.split()[0])


def load_config():
    """Load config.json. Create default if missing."""
    cfg_path = os.path.join(PROJECT_ROOT, "config.json")
    if not os.path.exists(cfg_path):
        logger.warning("config.json not found — creating default.")
        sm = SessionManager(config_path=cfg_path)
        return sm.config
    with open(cfg_path) as f:
        cfg = json.load(f)
    logger.info("config.json loaded (mode=%s, provider=%s, capital=\u20b9%.0f)",
                 cfg.get("mode"), cfg.get("provider"), cfg["risk"]["capital"])
    return cfg


def ensure_pyi3_core():
    """Ensure nsefo_core Rust extension is importable. Auto-install wheel if missing."""
    try:
        import nsefo_core
        nsefo_core.get_rsi_list([1, 2, 3, 4, 5], 3)
        logger.info("nsefo_core Rust extension loaded.")
        return True
    except ImportError:
        logger.warning("nsefo_core not found in site-packages.")

    wheel_dir = os.path.join(PROJECT_ROOT, "nsefo_core", "target", "wheels")
    if not os.path.exists(wheel_dir):
        logger.error("nsefo_core wheel directory not found.")
        logger.error("Run: python install.py   (Linux: ./install)")
        sys.exit(1)

    whl_files = [f for f in os.listdir(wheel_dir) if f.endswith(".whl")]
    if not whl_files:
        logger.error("No .whl file found in %s", wheel_dir)
        logger.error("Run: python install.py   (Linux: ./install)")
        sys.exit(1)

    whl_path = os.path.join(wheel_dir, whl_files[0])
    logger.info("Installing wheel: %s", whl_files[0])
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", whl_path, "--force-reinstall", "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error("Wheel install failed:\n%s", result.stderr[-500:])
        sys.exit(1)

    try:
        import nsefo_core
        nsefo_core.get_rsi_list([1, 2, 3, 4, 5], 3)
        logger.info("nsefo_core installed and verified.")
    except Exception as e:
        logger.error("nsefo_core import failed after install: %s", e)
        sys.exit(1)


def verify_connectivity(cfg, interactive=True):
    """Attempt broker.login() to verify credentials. Skip with --non-interactive."""
    if not interactive:
        logger.info("Skipping connectivity check (non-interactive mode).")
        return True

    provider = cfg.get("provider", "")
    required_fields = {
        "client_id": cfg.get("client_id", ""),
        "access_token": cfg.get("access_token", ""),
    }
    if provider == "geojit":
        required_fields["password"] = cfg.get("password", "")
        required_fields["yob"] = cfg.get("yob", "")
    elif provider == "paytm_money":
        required_fields["client_secret"] = cfg.get("client_secret", "")

    missing = [k for k, v in required_fields.items() if not v]
    if missing:
        logger.error("Missing credentials for %s: %s", provider, ", ".join(missing))
        logger.error("Run: python run.py --setup   (Linux: ./run.py --setup)")
        return False

    try:
        sm = SessionManager()
        broker = sm.get_broker()
        if broker and broker.login(
            password=cfg.get("password", ""),
            yob=cfg.get("yob", ""),
            totp_secret=cfg.get("totp_secret", ""),
        ):
            logger.info("[OK] %s connection verified.", provider.upper())
            return True
        logger.error("[FAIL] %s authentication failed. Run: python run.py --setup", provider.upper())
        return False
    except Exception as e:
        logger.error("[FAIL] Connectivity check error: %s", e)
        return False


def start_web_dashboard(bg=True):
    """Launch FastAPI dashboard on port 8899. Pass bg=False to run in this process."""
    logger.info("[INIT] Web Terminal on http://localhost:8899 ...")
    try:
        cmd = [sys.executable, "-m", "uvicorn",
               "dashboards.web.app:app",
               "--host", "0.0.0.0", "--port", "8899"]
        if bg:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            cwd=PROJECT_ROOT)
        else:
            subprocess.run(cmd, cwd=PROJECT_ROOT)
    except Exception as e:
        logger.error("Web dashboard failed: %s", e)


def run_setup_wizard():
    """Re-run the install.py configuration wizard (interactive, asks all params)."""
    logger.info("Launching configuration wizard...")
    try:
        from install import get_credentials
        cfg_path = os.path.join(PROJECT_ROOT, "config.json")
        existing = {}
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                existing = json.load(f)

        new_cfg = get_credentials(existing)

        with open(cfg_path, "w") as f:
            json.dump(new_cfg, f, indent=4)
        logger.info("Configuration saved to config.json.")

        # Quick connectivity verification
        print("\n[CONNECTIVITY CHECK]")
        verify_connectivity(new_cfg, interactive=True)
        print("\nSetup complete. Run: python run.py   (Linux: ./nsefo)")
    except Exception as e:
        logger.error("Setup wizard failed: %s", e)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 52)
    print("  NSEFO MASTER PRO - SYSTEM STARTUP")
    print("=" * 52 + "\n")

    check_python_version()

    # Parse flags
    args = sys.argv[1:]
    run_setup = "--setup" in args
    non_interactive = "--non-interactive" in args or "-y" in args
    # Core setup — always runs
    ensure_pyi3_core()
    cfg = load_config()

    if run_setup:
        run_setup_wizard()
        return

    if not non_interactive:
        if not verify_connectivity(cfg, interactive=True):
            logger.warning("Proceeding anyway (--non-interactive not set).")

    # ── Full application (GUI + trading engine) ─────────────────────────────

    print("\n" + "=" * 52)
    print("  MASTER PRO IS LIVE")
        print("=" * 52)
        print(f"  Web Console  : http://localhost:8899")
        print(f"  Trading Mode: {cfg.get('mode', 'paper').upper()}")
        print(f"  Capital     : \u20b9{cfg['risk']['capital']:,.0f}")
        print(f"  Broker      : {cfg.get('provider', 'dhan').upper()}")
        print("  Press Ctrl+C to terminate.\n")

        # Start web dashboard in background
        start_web_dashboard(bg=True)

        # Launch the GUI — import start_master_pro as a library (NOT subprocess)
        # This keeps a single Python process with one PYTHONPATH
        try:
            import start_master_pro
            # Ensure provider from config is propagated
            sm = SessionManager()
            if sm.config.get("provider"):
                cfg["provider"] = sm.config["provider"]
            start_master_pro.run_gui(cfg)
        except ImportError as e:
            logger.error("Failed to import start_master_pro: %s", e)
            logger.error("Ensure all dependencies: pip install -r requirements.txt")
            sys.exit(1)


if __name__ == "__main__":
    main()