from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from client.controller import background
from client.gui.styles import configure_table, display_time, style_table_item
from client.network import NetworkClient


class AuditTab(QWidget):
    def __init__(self, network_client: NetworkClient, parent=None):
        super().__init__(parent)
        self.network = network_client
        self._init_ui()
        self.load_audit()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(QLabel("Administration activity", objectName="sectionTitle"))
        hint = QLabel("Recent account and conversation changes, newest first.", objectName="hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

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
        configure_table(
            self.table, stretch=2, widths={0: 64, 1: 190, 3: 160, 4: 110, 5: 94, 6: 180}
        )
        self.table.setAccessibleName("Administrative audit records")
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
            self.table.setItem(row, 1, QTableWidgetItem(display_time(e["created_at"])))
            self.table.setItem(
                row, 2, QTableWidgetItem(f"{e['actor_username']} (id={e['actor_id']})")
            )
            self.table.setItem(row, 3, QTableWidgetItem(e["action"]))
            self.table.setItem(row, 4, QTableWidgetItem(e["target_type"]))
            target_id = "" if e["target_id"] is None else str(e["target_id"])
            self.table.setItem(row, 5, QTableWidgetItem(target_id))
            self.table.setItem(row, 6, QTableWidgetItem(e["details"] or "—"))
            for column in range(7):
                style_table_item(
                    self.table.item(row, column),
                    muted=column in {0, 1, 4, 5},
                    centered=column in {0, 5},
                )
            self.table.item(row, 1).setToolTip(e["created_at"])
