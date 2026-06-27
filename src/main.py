import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from gui_converter import ConverterWidget
from gui_logger import LoggerWindow

if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    icon_path = Path(__file__).resolve().parent / "attributes" / "ALM.ico"
    app.setWindowIcon(QIcon(str(icon_path)))

    # Initialize the logger
    logger = LoggerWindow()
    logger.setWindowIcon(QIcon(str(icon_path)))
    logger.resize(1060, 550)
    logger.show()

    # Initial print in the logger
    logger.initial_print()

    # Initialize the main window
    window = ConverterWidget(logger)
    logger.set_main_window(window)
    window.show()

    sys.exit(app.exec())