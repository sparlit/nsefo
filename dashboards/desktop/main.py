import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QTableWidget, QLineEdit, QPushButton, QComboBox, QTabWidget,
    QFormLayout, QProgressBar, QFrame
)
from PySide6.QtCore import QTimer, Qt
from python_app.broker.session_manager import SessionManager

class KanbanColumn(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel(f"<b>{title}</b>"))
        self.list_layout = QVBoxLayout()
        self.layout.addLayout(self.list_layout)
        self.layout.addStretch()

    def add_item(self, text):
        label = QLabel(text)
        label.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc; padding: 5px;")
        self.list_layout.addWidget(label)

class DashboardWindow(QMainWindow):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.setWindowTitle("NSEFO Master Pro Expert - Trading Terminal")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Expert Terminal Tab (Kanban)
        self.terminal_tab = QWidget()
        self.terminal_layout = QVBoxLayout(self.terminal_tab)

        self.summary_bar = QHBoxLayout()
        self.summary_bar.addWidget(QLabel("Capital: 1,000,000"))
        self.summary_bar.addWidget(QLabel("PNL: <font color='green'>+5,400</font>"))
        self.terminal_layout.addLayout(self.summary_bar)

        self.kanban_layout = QHBoxLayout()
        self.cols = {
            "SCANNING": KanbanColumn("SCANNING"),
            "SIGNALS": KanbanColumn("SIGNALS"),
            "ACTIVE": KanbanColumn("ACTIVE"),
            "CLOSED": KanbanColumn("CLOSED")
        }
        for col in self.cols.values():
            self.kanban_layout.addWidget(col)

        self.terminal_layout.addLayout(self.kanban_layout)

        # Config Tab
        from dashboards.desktop.main import ConfigTab # local import
        self.config_tab = ConfigTab(self.session_manager)

        self.tabs.addTab(self.terminal_tab, "Expert Terminal")
        self.tabs.addTab(self.config_tab, "Settings")

        # Initial Demo Items
        self.cols["SCANNING"].add_item("NIFTY [Brain: 85%]")
        self.cols["SIGNALS"].add_item("BANKNIFTY BUY @ 48000")

class ConfigTab(QWidget):
    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["paper", "live"])
        self.client_id = QLineEdit(session_manager.config.get("client_id", ""))
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self.save_cfg)

        self.form.addRow("Mode:", self.mode_combo)
        self.form.addRow("Client ID:", self.client_id)
        self.layout.addLayout(self.form)
        self.layout.addWidget(self.save_btn)

    def save_cfg(self):
        new_cfg = self.session_manager.config
        new_cfg['mode'] = self.mode_combo.currentText()
        new_cfg['client_id'] = self.client_id.text()
        self.session_manager.save_config(new_cfg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    sm = SessionManager()
    win = DashboardWindow(sm)
    win.show()
    # sys.exit(app.exec()) # In sandbox we don't exec
