"""
    Entry point to the application
"""

from PySide6.QtWidgets import QApplication
import sys
from src.ui_main_window import MainWindow

def main() -> None:
    """
        Launches a GUI application
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()