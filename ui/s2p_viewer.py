# ui/s2p_viewer.py

import os
import numpy as np
import skrf as rf
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class S2PViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("S2P Viewer")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.load_button = QPushButton("Load .s2p File")
        self.load_button.clicked.connect(self.load_s2p)
        self.layout.addWidget(self.load_button)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

    def load_s2p(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open S2P File", "", "S2P files (*.s2p)")
        if not path:
            return

        try:
            net = rf.Network(path)
            freq = net.f / 1e9  # GHz
            s11 = 20 * np.log10(np.abs(net.s[:, 0, 0]))
            s21 = 20 * np.log10(np.abs(net.s[:, 1, 0]))
            s12 = 20 * np.log10(np.abs(net.s[:, 0, 1]))
            s22 = 20 * np.log10(np.abs(net.s[:, 1, 1]))

            self.populate_table(freq, s11, s21, s12, s22)
            self.plot_data(freq, s11, s21, s12, s22)
        except Exception as e:
            self.table.clear()
            self.figure.clear()
            self.layout.addWidget(QLabel(f"Error: {str(e)}"))

    def populate_table(self, freq, s11, s21, s12, s22):
        self.table.setRowCount(len(freq))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Freq (GHz)", "S11 (dB)", "S21 (dB)", "S12 (dB)", "S22 (dB)"])

        for i in range(len(freq)):
            self.table.setItem(i, 0, QTableWidgetItem(f"{freq[i]:.3f}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{s11[i]:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{s21[i]:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{s12[i]:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{s22[i]:.2f}"))

    def plot_data(self, freq, s11, s21, s12, s22):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(freq, s11, label="S11")
        ax.plot(freq, s21, label="S21")
        ax.plot(freq, s12, label="S12")
        ax.plot(freq, s22, label="S22")
        ax.set_title("S-Parameters")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Magnitude (dB)")
        ax.grid(True)
        ax.legend()
        self.canvas.draw()
