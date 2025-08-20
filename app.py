# app.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QLabel
)

# --- Import tab widgets ---
# Make sure these files exist:
#   ui/main_window.py  -> class MainWindow(QWidget)
#   ui/s2p_viewer.py   -> class S2PViewer(QWidget)
#   ui/im_viewer.py    -> class IMViewer(QWidget)
from ui.main_window import MainWindow
from ui.s2p_viewer import S2PViewer
from ui.im_viewer import IMViewer


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Board Test Pluggable")
        self.resize(1400, 900)

        # Central widget + layout
        central = QWidget(self)
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)

        # Tabs
        self.tabs = QTabWidget(self)
        vbox.addWidget(self.tabs)

        # --- Tab 1: Layout Editor ---
        self.main_window = MainWindow()            # <-- must be an INSTANCE of QWidget
        self.tabs.addTab(self.main_window, "Layout Editor")

        # --- Tab 2: S2P Viewer ---
        self.s2p_viewer = S2PViewer()              # <-- must be an INSTANCE of QWidget
        self.tabs.addTab(self.s2p_viewer, "S2P Viewer")

        # --- Tab 3: IM Viewer ---
        self.im_viewer = IMViewer()                # <-- must be an INSTANCE of QWidget
        self.tabs.addTab(self.im_viewer, "IM Viewer")


def main():
    # Optional: better scaling on HiDPI displays
    QApplication.setAttribute
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
