# app.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget
from ui.main_window import BoardTesterApp
from ui.s2p_viewer import S2PViewer
from ui.im_viewer import IMViewer

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Board Test Pluggable")
        self.setGeometry(100, 100, 1400, 900)

        # Main layout with tabs
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Tab 1: Layout Editor
        self.main_window = MainWindow()
        self.tabs.addTab(self.main_window, "Layout Editor")

        # Tab 2: S2P Viewer
        self.s2p_viewer = S2PViewer()
        self.tabs.addTab(self.s2p_viewer, "S2P Viewer")

        # Tab 3: IM Viewer
        self.im_viewer = IMViewer()
        self.tabs.addTab(self.im_viewer, "IM Viewer")

def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
