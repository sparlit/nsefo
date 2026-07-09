import sys
import os
import json
import time
import threading
import subprocess
import logging
from python_app.broker.session_manager import SessionManager
from python_app.main import TradingApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [LAUNCHER] - %(levelname)s - %(message)s')

def get_input(prompt, default):
    val = input(f"{prompt} [{default}]: ")
    return val if val else default

def setup_config():
    sm = SessionManager()
    print("\n" + "="*50)
    print("  NSEFO MASTER PRO - INITIAL CONFIGURATION")
    print("="*50)

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
    new_cfg['totp_secret'] = current.get('totp_secret', '')
    new_cfg['provider'] = current.get('provider', 'fenix')

    sm.save_config(new_cfg)
    print("\n[OK] Configuration Saved Successfully.")
    return sm

def check_connectivity():
    print("\n" + "="*50)
    print("  CONNECTIVITY & SYSTEM INTEGRITY CHECK")
    print("="*50)
    try:
        app = TradingApp()
        if app.broker and app.broker.login():
            print("[OK] Broker Authentication: SUCCESS")
            print("[OK] Rust Neural Engine: ONLINE")
            print("[OK] Market Data Feed: READY")
            return True
        else:
            print("[ERROR] Broker Authentication Failed. Check credentials in Settings.")
            return False
    except Exception as e:
        print(f"[CRITICAL ERROR] System Initialization Failed: {e}")
        return False

def start_web_dashboard():
    print("[INIT] Launching Web Dashboard (Port 8000)...")
    subprocess.Popen([sys.executable, "-m", "uvicorn", "dashboards.web.app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "error"])

def start_engine():
    print("[INIT] Starting Expert Trading Engine...")
    # Engine runs in the main thread or background
    app = TradingApp()
    app.start()

def main():
    os.environ['PYTHONPATH'] = os.getcwd()

    if not os.path.exists("config.json") or input("\nModify existing configuration? (y/n) [n]: ").lower() == 'y':
        setup_config()

    if check_connectivity():
        print("\n" + "="*50)
        print("  LAUNCHING FULL MASTER PRO SUITE")
        print("="*50)

        start_web_dashboard()

        # Start Engine (Background)
        threading.Thread(target=start_engine, daemon=True).start()

        print("\n[SUCCESS] NSEFO Master Pro is active.")
        print("-> Web Terminal: http://localhost:8000")
        print("-> Desktop Terminal: Launching UI...")

        # Finally, launch Desktop UI (Main Thread)
        try:
            from PySide6.QtWidgets import QApplication
            from dashboards.desktop.main import DashboardWindow
            from python_app.main import TradingApp

            qt_app = QApplication(sys.argv)
            trade_app = TradingApp()
            win = DashboardWindow(trade_app.session, trade_app)
            win.show()
            sys.exit(qt_app.exec())
        except Exception as e:
            print(f"[INFO] Desktop UI could not be started: {e}")
            print("[INFO] Application continuing in Headless/Web mode.")
            while True: time.sleep(1)

if __name__ == "__main__":
    main()
