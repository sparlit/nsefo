import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QTableWidget, QLineEdit, QPushButton, QComboBox, QTabWidget, QFormLayout
)
from PySide6.QtCore import QTimer
import json
import os

class ConfigTab(QWidget):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.layout = QVBoxLayout(self)

        self.form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["paper", "live"])

        self.client_id_input = QLineEdit()
        self.access_token_input = QLineEdit()
        self.access_token_input.setEchoMode(QLineEdit.Password)
        self.totp_secret_input = QLineEdit()

        self.capital_input = QLineEdit()
        self.risk_input = QLineEdit()

        self.form.addRow("Trading Mode:", self.mode_combo)
        self.form.addRow("Client ID:", self.client_id_input)
        self.form.addRow("Access Token:", self.access_token_input)
        self.form.addRow("TOTP Secret:", self.totp_secret_input)
        self.form.addRow("Initial Capital:", self.capital_input)
        self.form.addRow("Max Risk/Trade (%):", self.risk_input)

        self.save_btn = QPushButton("Save & Re-initialize")
        self.save_btn.clicked.connect(self.save_config)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.save_btn)

        self.load_data()

    def load_data(self):
        cfg = self.session_manager.config
        self.mode_combo.setCurrentText(cfg.get("mode", "paper"))
        self.client_id_input.setText(cfg.get("client_id", ""))
        self.access_token_input.setText(cfg.get("access_token", ""))
        self.totp_secret_input.setText(cfg.get("totp_secret", ""))

        risk = cfg.get("risk", {})
        self.capital_input.setText(str(risk.get("capital", 100000)))
        self.risk_input.setText(str(risk.get("max_risk_per_trade_percent", 1.0)))

    def save_config(self):
        new_cfg = {
            "mode": self.mode_combo.currentText(),
            "client_id": self.client_id_input.text(),
            "access_token": self.access_token_input.text(),
            "totp_secret": self.totp_secret_input.text(),
            "risk": {
                "capital": float(self.capital_input.text() or 100000),
                "max_risk_per_trade_percent": float(self.risk_input.text() or 1.0)
            }
        }
        self.session_manager.save_config(new_cfg)
        print("Config saved from Desktop UI.")

class DashboardWindow(QMainWindow):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.setWindowTitle("NSEFO Master Pro Expert - Trading Terminal")
        self.resize(900, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Main Trading Tab
        self.trading_tab = QWidget()
        self.trading_layout = QVBoxLayout(self.trading_tab)
        self.trading_layout.addWidget(QLabel("Active Trades & Kanban View"))
        self.trades_table = QTableWidget(0, 5)
        self.trades_table.setHorizontalHeaderLabels(["Symbol", "Type", "LTP", "P&L", "Status"])
        self.trading_layout.addWidget(self.trades_table)

        # Config Tab
        self.config_tab = ConfigTab(self.session_manager)

        self.tabs.addTab(self.trading_tab, "Terminal")
        self.tabs.addTab(self.config_tab, "Configuration")

if __name__ == "__main__":
    # This section for manual run; when integrated, TradingApp will launch this.
    print("Desktop Dashboard class initialized.")

def launch_dashboard(sm):
    app = QApplication(sys.argv)
    window = DashboardWindow(sm)
    window.show()
    sys.exit(app.exec())
