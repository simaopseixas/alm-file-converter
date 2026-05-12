import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from gui import ConverterWidget


if __name__ == "__main__":
    print("=============================")
    print("ALM Microscopy File Converter")
    print("=============================")

    app = QApplication(sys.argv)

    icon_path = Path(__file__).resolve().parent / "attributes" / "ALM.ico"
    app.setWindowIcon(QIcon(str(icon_path)))

    window = ConverterWidget()
    window.show()

    sys.exit(app.exec())
