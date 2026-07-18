"""
NSEFO Master Pro - GUI Runner & Configuration Wizard
====================================================
This module is typically NOT run directly. Import and call from run.py:
    import start_master_pro
    start_master_pro.run_gui(cfg)         # Launch GUI app
    start_master_pro.setup_wizard()      # Re-run config wizard

Or for backwards compatibility (deprecated):
    python start_master_pro.py            # Same as: python run.py
    python start_master_pro.py --setup    # Same as: python run.py --setup
"""
import sys
import os
import time
import threading
import logging
import json

# Ensure PROJECT_ROOT is in PYTHONPATH for direct script execution
if __name__ == "__main__" or "start_master_pro" in str(sys.argv):
    _root = os.path.dirname(os.path.abspath(__file__))
    os.environ["PYTHONPATH"] = _root + os.pathsep + os.environ.get("PYTHONPATH", "")

from python_app.broker.session_manager import SessionManager
from python_app.main import TradingApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MASTER-PRO] - %(levelname)s - %(message)s"
)


def _prompt(prompt_text: str, fallback):
    """Read input with fallback for non-interactive (EOF/signal)."""
    try:
        return input(prompt_text) or fallback
    except (EOFError, OSError):
        return fallback


def setup_wizard():
    """
    Re-run the configuration wizard.
    Delegates to install.py's get_credentials() for the complete, tested wizard.
    """
    print("\n" + "=" * 50)
    print("  NSEFO MASTER PRO - CONFIGURATION WIZARD")
    print("=" * 50)

    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    existing = {}
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            existing = json.load(f)

    try:
        from install import get_credentials
        new_cfg = get_credentials(existing)
    except Exception as e:
        logging.error("install.py wizard unavailable: %s", e)
        logging.info("Falling back to inline wizard...")
        # Inline fallback — only handles basic fields
        new_cfg = dict(existing)
        new_cfg["mode"] = _prompt(f"Mode (live/paper) [{existing.get('mode', 'paper')}]: ",
                                  existing.get('mode', 'paper'))
        new_cfg["client_id"] = _prompt(f"Client ID [{existing.get('client_id', '')}]: ",
                                      existing.get('client_id', ''))
        new_cfg["access_token"] = _prompt(f"Access Token: ", existing.get('access_token', ''))

    with open(cfg_path, "w") as f:
        json.dump(new_cfg, f, indent=4)
    print("[OK] Configuration saved to config.json")

    # Verify
    print("\n[CONNECTIVITY CHECK]")
    try:
        sm = SessionManager()
        broker = sm.get_broker()
        if broker and broker.login():
            print("[OK] Connection verified.")
        else:
            print("[WARNING] Authentication failed. Check credentials.")
    except Exception as e:
        print(f"[WARNING] Connectivity check error: {e}")

    print("\nRe-run: python run.py   (Linux: ./nsefo)")


def run_gui(cfg=None):
    """
    Start the full GUI application:
      - TradingApp (broker login + market cycle)
      - Web dashboard (uvicorn, port 8899)
      - PySide6 desktop window

    Args:
        cfg: optional dict; if None, loads from config.json via SessionManager
    """
    if cfg is None:
        sm = SessionManager()
        cfg = sm.config

    print("\n" + "=" * 50)
    print("  NSEFO MASTER PRO - SYSTEM ACTIVATION")
    print("=" * 50)

    # Initialize TradingApp — broker login happens inside __init__
    try:
        app = TradingApp()
    except Exception as e:
        print(f"[CRITICAL] Failed to initialize TradingApp: {e}")
        sys.exit(1)

    if not app.broker or not app.broker.login():
        print("[CRITICAL] Authentication Failed.")
        print("Run: python run.py --setup   (Linux: ./run.py --setup)")
        sys.exit(1)

    # Web dashboard (port 8899) is launched by run.py before run_gui() is called.
    # Do NOT start it here to avoid port conflicts.

    # Start market cycle in background thread
    print("[INIT] Activating Neural Calculation Core...")
    threading.Thread(target=app.start, daemon=True).start()

    print("\n[SUCCESS] MASTER PRO IS LIVE")
    print("  Web Console  : http://localhost:8899")

    # Launch PySide6 desktop window — blocks until app closes
    try:
        from PySide6.QtWidgets import QApplication
        from dashboards.desktop.main import DashboardWindow
        qt_app = QApplication(sys.argv)
        win = DashboardWindow(app.session, app)
        win.show()
        sys.exit(qt_app.exec())
    except ImportError:
        print("[INFO] PySide6 not installed — running in headless mode.")
        print("[INFO] Web Console available at: http://localhost:8899")
        print("Press Ctrl+C to terminate.")
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"[WARN] Desktop UI error: {e}")
        print("[INFO] Operating in headless/web mode.")
        print("Press Ctrl+C to terminate.")
        while True:
            time.sleep(1)


# ─────────────────────────────────────────────────────────────────────────────
# Backwards-compatible main() for: python start_master_pro.py
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if args and args[0] == "--setup":
        setup_wizard()
    else:
        # Mirror run.py's startup sequence so python start_master_pro.py works alone
        _root = os.path.dirname(os.path.abspath(__file__))
        os.environ["PYTHONPATH"] = _root + os.pathsep + os.environ.get("PYTHONPATH", "")

        # Ensure nsefo_core
        try:
            import nsefo_core
            nsefo_core.get_rsi_list([1, 2, 3], 2)
        except ImportError:
            print("[ERROR] nsefo_core not loaded. Run: python install.py")
            sys.exit(1)

        run_gui()


if __name__ == "__main__":
    main()