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

    def update_items(self, new_items: list):
        for i in reversed(range(self.list_layout.count() - 1)):
            w = self.list_layout.itemAt(i).widget()
            if w: w.setParent(None)

        for item in new_items:
            label = QLabel(str(item))
            label.setStyleSheet("background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin-bottom: 8px; color: #1e293b; font-weight: 500;")
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
        self.lots = QLineEdit(str(sm.config['risk'].get('fixed_lots', 1)))

        self.save_btn = QPushButton("COMMIT OPERATIONAL SETTINGS")
        self.save_btn.setStyleSheet("background: #166534; color: white; padding: 15px; font-weight: 900; border-radius: 8px;")
        self.save_btn.clicked.connect(self.save)

        self.form.addRow("TRADING MODE:", self.mode)
        self.form.addRow("DHAN CLIENT ID:", self.cid)
        self.form.addRow("API ACCESS TOKEN:", self.token)
        self.form.addRow("FIXED LOT SIZE:", self.lots)
        self.layout.addLayout(self.form)
        self.layout.addWidget(self.save_btn)
        self.layout.addStretch()

    def save(self):
        new_cfg = self.sm.config
        new_cfg.update({"mode": self.mode.currentText(), "client_id": self.cid.text(), "access_token": self.token.text()})
        new_cfg['risk']['fixed_lots'] = int(self.lots.text())
        self.sm.save_config(new_cfg)
        logging.info("Configuration State Synchronized.")

class DashboardWindow(QMainWindow):
    def __init__(self, sm: SessionManager, app_instance):
        super().__init__()
        self.sm = sm
        self.app = app_instance
        self.setWindowTitle("NSEFO MASTER PRO EXPERT - PRODUCTION TERMINAL")
        self.resize(1200, 850)
        self.setStyleSheet("QMainWindow { background-color: #f1f5f9; }")

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.terminal = QWidget()
        self.terminal_layout = QVBoxLayout(self.terminal)

        self.kanban = QHBoxLayout()
        self.cols = {
            "SCANNING": KanbanColumn("SCANNING"),
            "SIGNAL": KanbanColumn("CONVICTION SIGNALS"),
            "ACTIVE": KanbanColumn("ACTIVE ORDERS"),
            "CLOSED": KanbanColumn("CLOSED POSITIONS")
        }
        for c in self.cols.values(): self.kanban.addWidget(c)
        self.terminal_layout.addLayout(self.kanban)

        self.tabs.addTab(self.terminal, "LIVE TERMINAL")
        self.tabs.addTab(ConfigTab(self.sm), "SYSTEM CONFIG")

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

    def refresh(self):
        from python_app.core.state import global_state
        with global_state._lock:
            active_list = [f"<b>{t['symbol']}</b><br>{t['side']} @ {t['price']}<br><small>Qty: {t['qty']}</small>" for t in global_state.kanban["ACTIVE"]]
        self.cols["ACTIVE"].update_items(active_list)

        scanning_list = [f"<b>{s}</b><br><small>Neural Cluster Analysis Active...</small>" for s in self.app.watch_list]
        self.cols["SCANNING"].update_items(scanning_list)

if __name__ == "__main__":
    from python_app.main import TradingApp
    qt_app = QApplication(sys.argv)
    trade_app = TradingApp()
    win = DashboardWindow(trade_app.session, trade_app)
    win.show()
    sys.exit(qt_app.exec())
