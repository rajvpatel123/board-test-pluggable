# app.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QPushButton
from ui.main_window import MainWindow
from ui.s2p_viewer import S2PViewer  # This is the new viewer tab we added

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Board Test Pluggable")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget with layout and tabs
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Add main layout editor tab
        self.main_window = MainWindow()
        self.tabs.addTab(self.main_window, "Layout Editor")

        # Add S2P Viewer tab
        self.s2p_viewer = S2PViewer()
        self.tabs.addTab(self.s2p_viewer, "S2P Viewer")

        # Optional: Add a global button if needed (not inside tabs)
        # self.load_button = QPushButton("Do Something")
        # self.layout.addWidget(self.load_button)

def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
