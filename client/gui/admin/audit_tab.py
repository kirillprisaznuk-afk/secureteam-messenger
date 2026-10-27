from PyQt5.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from client.controller import background
from client.network import NetworkClient


class AuditTab(QWidget):
    def __init__(self, network_client: NetworkClient, parent=None):
        super().__init__(parent)
        self.network = network_client
        self._init_ui()
        self.load_audit()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_audit)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Time", "Actor", "Action", "Target type", "Target ID", "Details"]
        )
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        layout.addWidget(self.table)

    @background
    def load_audit(self):
        resp = yield lambda: self.network.get_audit_entries()
        if not resp.get("success"):
            QMessageBox.critical(self, "Error", resp.get("error", "Failed to load audit log"))
            return

        entries = resp.get("entries", [])
        self.table.setRowCount(len(entries))

        for row, e in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(str(e["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(e["created_at"]))
            self.table.setItem(
                row, 2, QTableWidgetItem(f"{e['actor_username']} (id={e['actor_id']})")
            )
            self.table.setItem(row, 3, QTableWidgetItem(e["action"]))
            self.table.setItem(row, 4, QTableWidgetItem(e["target_type"]))
            target_id = "" if e["target_id"] is None else str(e["target_id"])
            self.table.setItem(row, 5, QTableWidgetItem(target_id))
            self.table.setItem(row, 6, QTableWidgetItem(e["details"] or ""))
