import sys
import os
import time
import threading
import subprocess
import logging
from python_app.broker.session_manager import SessionManager
from python_app.main import TradingApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MASTER-PRO] - %(levelname)s - %(message)s')


def _prompt(prompt_text: str, fallback):
    """Read from stdin non-interactively if no tty is available; return fallback."""
    try:
        return input(prompt_text) or fallback
    except (EOFError, OSError):
        return fallback


def setup_wizard():
    sm = SessionManager()
    print("\n" + "╔" + "="*48 + "╗")
    print("║  NSEFO MASTER PRO - CONFIGURATION WIZARD        ║")
    print("╚" + "="*48 + "╝")

    current = sm.config
    cfg = {}
    cfg['mode'] = _prompt(f"Trading Mode (live/paper) [{current.get('mode', 'paper')}]: ", current.get('mode', 'paper'))
    cfg['client_id'] = _prompt(f"Dhan Client ID [{current.get('client_id', '')}]: ", current.get('client_id', ''))
    cfg['access_token'] = _prompt(f"API Access Token [HIDDEN]: ", current.get('access_token', ''))

    risk = current.get('risk', {})
    new_risk = {
        'capital': float(_prompt(f"Operational Capital [{risk.get('capital', 1000000)}]: ", risk.get('capital', 1000000))),
        'fixed_lots': int(_prompt(f"Fixed Lot Count [{risk.get('fixed_lots', 1)}]: ", risk.get('fixed_lots', 1))),
        'max_risk_per_trade_percent': risk.get('max_risk_per_trade_percent', 1.0),
        'daily_max_loss': risk.get('daily_max_loss', 5000.0)
    }

    cfg['risk'] = new_risk
    cfg['totp_secret'] = _prompt(f"TOTP Secret [{current.get('totp_secret', '')}]: ", current.get('totp_secret', ''))
    cfg['provider'] = 'fenix'

    sm.save_config(cfg)
    print("\n[OK] Configuration successfully persisted to config.json")

    print("\nValidating Connectivity...")
    app = TradingApp()
    if app.broker and app.broker.login():
        print("[OK] Connection to Dhan API Verified.")
    else:
        print("[WARNING] Connection failed. Please check credentials.")

def run_application():
    os.environ['PYTHONPATH'] = os.getcwd()
    print("\n" + "╔" + "="*48 + "╗")
    print("║  NSEFO MASTER PRO - SYSTEM ACTIVATION           ║")
    print("╚" + "="*48 + "╝")

    app = TradingApp()
    if not app.broker or not app.broker.login():
        print("[CRITICAL] Authentication Failed. Run 'install' to reconfigure.")
        sys.exit(1)

    # 1. Start Web Dashboard
    print("[INIT] Launching Web Terminal (Port 8000)...")
    subprocess.Popen([sys.executable, "-m", "uvicorn", "dashboards.web.app:app", "--host", "0.0.0.0", "--port", "8000"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. Start Engine
    print("[INIT] Activating Neural Calculation Core...")
    threading.Thread(target=app.start, daemon=True).start()

    print("\n[SUCCESS] MASTER PRO IS LIVE")
    print("-> Web Console: http://localhost:8000")

    # 3. Launch Desktop Terminal
    try:
        from PySide6.QtWidgets import QApplication
        from dashboards.desktop.main import DashboardWindow
        qt_app = QApplication(sys.argv)
        win = DashboardWindow(app.session, app)
        win.show()
        sys.exit(qt_app.exec())
    except Exception as e:
        print(f"[INFO] Desktop UI Mode Unavailable: {e}")
        print("[INFO] Operating in Headless/Web mode. Press Ctrl+C to terminate.")
        while True: time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        setup_wizard()
    else:
        run_application()
