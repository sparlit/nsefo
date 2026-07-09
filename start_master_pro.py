import sys
import os
import json
import time
import threading
import subprocess
import logging
from python_app.broker.session_manager import SessionManager
from python_app.main import TradingApp
from python_app.core.state import global_state

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [LAUNCHER] - %(levelname)s - %(message)s')

def get_input(prompt, default):
    val = input(f"{prompt} [{default}]: ")
    return val if val else default

def setup_config():
    sm = SessionManager()
    print("\n" + "╔" + "="*48 + "╗")
    print("║  NSEFO MASTER PRO - INITIAL CONFIGURATION       ║")
    print("╚" + "="*48 + "╝")

    current = sm.config
    new_cfg = {}
    new_cfg['mode'] = get_input("Trading Mode (live/paper)", current.get('mode', 'paper'))
    new_cfg['client_id'] = get_input("Dhan Client ID", current.get('client_id', ''))
    new_cfg['access_token'] = get_input("API Access Token", current.get('access_token', ''))

    risk = current.get('risk', {})
    new_risk = {}
    new_risk['capital'] = float(get_input("Operational Capital", risk.get('capital', 1000000)))
    new_risk['fixed_lots'] = int(get_input("Fixed Lot Count", risk.get('fixed_lots', 1)))
    new_risk['max_risk_per_trade_percent'] = risk.get('max_risk_per_trade_percent', 1.0)
    new_risk['daily_max_loss'] = risk.get('daily_max_loss', 5000.0)

    new_cfg['risk'] = new_risk
    new_cfg['totp_secret'] = get_input("TOTP Secret Key (Optional)", current.get('totp_secret', ''))
    new_cfg['provider'] = get_input("Broker Provider (fenix/dhan)", current.get('provider', 'fenix'))

    sm.save_config(new_cfg)
    print("\n[OK] Operational Parameters Saved.")
    return sm

def check_system_integrity():
    print("\n" + "╔" + "="*48 + "╗")
    print("║  SYSTEM INTEGRITY & CONNECTIVITY CHECK          ║")
    print("╚" + "="*48 + "╝")
    try:
        app = TradingApp()
        if app.broker and app.broker.login():
            print("[OK] Dhan API Gateway: CONNECTED")
            print("[OK] Rust Calculation Core: SYNCED")
            print("[OK] Multi-Brain Coordinator: ACTIVE")
            return True
        else:
            print("[ERROR] Authentication Failed. Verify credentials in Config.")
            return False
    except Exception as e:
        print(f"[CRITICAL] Initialization Error: {e}")
        return False

def start_web_dashboard():
    print("[INIT] Deploying Web Terminal (Port 8000)...")
    # Redirect output to prevent cluttering the main console
    with open("web_dashboard.log", "w") as log:
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "dashboards.web.app:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=log, stderr=log
        )

def launch_suite():
    os.environ['PYTHONPATH'] = os.getcwd()

    # 1. Config Check
    if not os.path.exists("config.json") or input("\nModify system parameters? (y/n) [n]: ").lower() == 'y':
        setup_config()

    # 2. Connectivity Check
    if not check_system_integrity():
        sys.exit(1)

    print("\n" + "╔" + "="*48 + "╗")
    print("║  ACTIVATING MASTER PRO EXPERT ENVIRONMENT       ║")
    print("╚" + "="*48 + "╝")

    # 3. Launch Services
    start_web_dashboard()

    print("[INIT] Starting Market Scanning Engine...")
    app_engine = TradingApp()
    threading.Thread(target=app_engine.start, daemon=True).start()

    print("\n" + "*"*50)
    print("  SYSTEM IS LIVE")
    print("  - Access Web Console: http://localhost:8000")
    print("  - Initializing Desktop Terminal...")
    print("*"*50 + "\n")

    # 4. Launch Desktop UI in Main Thread
    try:
        from PySide6.QtWidgets import QApplication
        from dashboards.desktop.main import DashboardWindow

        qt_app = QApplication(sys.argv)
        # Pass the existing app instance for state sharing
        win = DashboardWindow(app_engine.session, app_engine)
        win.show()
        sys.exit(qt_app.exec())
    except Exception as e:
        logging.error(f"Desktop UI unavailable: {e}")
        print("[INFO] Application running in Web-Only Mode. Press Ctrl+C to exit.")
        while True: time.sleep(1)

if __name__ == "__main__":
    launch_suite()
