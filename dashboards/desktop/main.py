import sys
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QTabWidget,
    QFormLayout, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from python_app.broker.session_manager import SessionManager

class KanbanColumn(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.layout = QVBoxLayout(self)
        self.header = QLabel(f"<b>{title}</b>")
        self.header.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.header)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

    def add_trade(self, trade_info: str):
        label = QLabel(trade_info)
        label.setStyleSheet("background: #e1f5fe; border-radius: 4px; padding: 10px; margin-bottom: 5px; color: #01579b;")
        self.list_layout.insertWidget(0, label)

class ConfigTab(QWidget):
    def __init__(self, sm: SessionManager):
        super().__init__()
        self.sm = sm
        self.layout = QVBoxLayout(self)
        self.form = QFormLayout()

        self.mode = QComboBox()
        self.mode.addItems(["paper", "live"])
        self.mode.setCurrentText(sm.config.get("mode", "paper"))

        self.cid = QLineEdit(sm.config.get("client_id", ""))
        self.token = QLineEdit(sm.config.get("access_token", ""))
        self.token.setEchoMode(QLineEdit.Password)

        self.capital = QLineEdit(str(sm.config['risk'].get('capital', 1000000)))
        self.fixed_lots = QLineEdit(str(sm.config['risk'].get('fixed_lots', 1)))

        self.save_btn = QPushButton("SAVE & SYNC SYSTEM")
        self.save_btn.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.save_btn.clicked.connect(self.save)

        self.form.addRow("Trading Mode:", self.mode)
        self.form.addRow("Dhan Client ID:", self.cid)
        self.form.addRow("API Access Token:", self.token)
        self.form.addRow("Operational Capital:", self.capital)
        self.form.addRow("<b>Fixed Lot Count:</b>", self.fixed_lots)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.save_btn)
        self.layout.addStretch()

    def save(self):
        new_cfg = self.sm.config
        new_cfg.update({
            "mode": self.mode.currentText(),
            "client_id": self.cid.text(),
            "access_token": self.token.text()
        })
        new_cfg['risk']['capital'] = float(self.capital.text() if self.capital.text() else 1000000)
        new_cfg['risk']['fixed_lots'] = int(self.fixed_lots.text() if self.fixed_lots.text() else 1)
        self.sm.save_config(new_cfg)
        logging.info("Desktop UI: Configuration persisted successfully.")

class DashboardWindow(QMainWindow):
    def __init__(self, sm: SessionManager, coordinator=None):
        super().__init__()
        self.sm = sm
        self.coordinator = coordinator
        self.setWindowTitle("NSEFO MASTER PRO - TRADING TERMINAL [STABLE]")
        self.resize(1200, 850)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.terminal = QWidget()
        self.terminal_layout = QVBoxLayout(self.terminal)

        self.kanban = QHBoxLayout()
        self.cols = {
            "SCANNING": KanbanColumn("SCANNING"),
            "SIGNAL": KanbanColumn("SIGNALS"),
            "ACTIVE": KanbanColumn("ACTIVE"),
            "CLOSED": KanbanColumn("CLOSED")
        }
        for c in self.cols.values(): self.kanban.addWidget(c)

        self.terminal_layout.addLayout(self.kanban)
        self.tabs.addTab(self.terminal, "EXPERT TERMINAL")
        self.tabs.addTab(ConfigTab(self.sm), "SYSTEM SETTINGS")

        self.timer = QTimer()
        self.timer.timeout.connect(self.sync_live_data)
        self.timer.start(2000)

    def sync_live_data(self):
        """Synchronizes Terminal UI with the live coordinator state."""
        if self.coordinator:
             # Real-time synchronization logic
             for order_id, trade in self.coordinator.active_trades.items():
                 self.cols["ACTIVE"].add_trade(f"{trade['symbol']} | {trade['side']} | Qty: {trade['quantity']}")
        else:
             logging.debug("Dashboard awaiting coordinator link...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    sm = SessionManager()
    win = DashboardWindow(sm)
    win.show()
    # Lifecycle managed by entry point
