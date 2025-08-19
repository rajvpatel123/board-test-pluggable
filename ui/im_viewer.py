# ui/im_viewer.py

import os
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QLabel


class IMViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IM Viewer")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.load_button = QPushButton("Load .im File")
        self.load_button.clicked.connect(self.load_im)
        self.layout.addWidget(self.load_button)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

    def load_im(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open .im File", "", "IM files (*.im)")
        if not path:
            return

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            # Parse all biasingcmd elements
            bias_data = []
            for cmd in root.findall(".//biasingcmd"):
                access = cmd.attrib.get("access", "")
                unit = cmd.attrib.get("unit", "")
                quiescent = cmd.attrib.get("quiescent", "")
                pulse = cmd.attrib.get("pulse", "")

                bias_data.append((access, unit, quiescent, pulse))

            self.populate_table(bias_data)

        except Exception as e:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Error"])
            self.table.setItem(0, 0, QTableWidgetItem(str(e)))

    def populate_table(self, data):
        self.table.clear()
        self.table.setR
