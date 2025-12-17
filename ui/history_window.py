from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PySide6.QtCore import QTimer, Qt
from database.db import fetch_all_logs


class HistoryWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lịch sử xe ra / vào")
        self.resize(900, 450)

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.last_row_count = 0

        self.setup_table()
        self.load_data()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_if_needed)
        self.timer.start(1500)

    def setup_table(self):
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Biển số", "Confidence", "Quyết định", "Ảnh", "Thời gian"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

    def load_data(self):
        rows = fetch_all_logs()
        self.last_row_count = len(rows)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                if c == 3:
                    item.setForeground(Qt.green if val == "ALLOW" else Qt.red)
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)

        self.table.resizeColumnsToContents()

    def refresh_if_needed(self):
        if len(fetch_all_logs()) != self.last_row_count:
            self.load_data()
