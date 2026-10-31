"""
    Entry point to the application
"""

# import PySide6 application container class
from PySide6.QtWidgets import QApplication
# import system module for accessing command line arguments and exiting application loop
import sys
# import MainWindow class from UI module
from src.ui.ui_main_window import MainWindow

# define main application execution function
def main() -> None:
    """
        Launches a GUI application
    """
    # instantiate central QApplication passing command line arguments
    app = QApplication(sys.argv)
    # construct main application window instance
    window = MainWindow()
    # render and display main window on screen
    window.show()
    # start Qt event loop and terminate Python process with returned exit code on window close
    sys.exit(app.exec())

# Ensure script only runs main() when executed directly as top-level script
if __name__ == "__main__":
    # call main entry point function
    main()