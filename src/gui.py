import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tooltip_manager import CustomToolTipManager


class ConverterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.attributes_dir = Path(__file__).resolve().parent / "attributes"
        self.tooltip_manager = CustomToolTipManager(self)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("ALM File Converter")
        self.setWindowIcon(QIcon(str(self.attributes_dir / "ALM.ico")))
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(9)

        self.batch_checkbox = QCheckBox("Batch Processing")
        self.batch_checkbox.setChecked(True)
        self.batch_checkbox.toggled.connect(self.update_button_text)

        self.batch_info_label = QLabel("i")
        self.batch_info_label.setObjectName("infoLabel")
        self.batch_info_label.setFixedSize(16, 16)
        self.batch_info_label.setAlignment(Qt.AlignCenter)
        self.batch_info_label.setCursor(Qt.PointingHandCursor)
        self.tooltip_manager.attach_tooltip(
            self.batch_checkbox,
            "Batch processing will convert all files in a folder.\n" \
            "Disable if you want to convert a single file.",
        )
        self.tooltip_manager.attach_tooltip(
            self.batch_info_label,
            "This program currently has support for:\n" \
            ".ims, .lif, .ome.tiff, ome.zarr"
        )

        self.convert_label = QLabel()

        self.format_combobox = QComboBox()
        self.format_combobox.addItems(["ome.zarr"])

        self.choose_button = QPushButton()
        self.choose_button.setFixedHeight(34)

        batch_row = QHBoxLayout()
        batch_row.setContentsMargins(0, 0, 0, 0)
        batch_row.setSpacing(6)
        batch_row.addWidget(self.batch_checkbox)
        batch_row.addStretch()
        batch_row.addWidget(self.batch_info_label)

        layout.addLayout(batch_row)
        layout.addWidget(self.convert_label, alignment=Qt.AlignLeft)
        layout.addWidget(self.format_combobox)
        layout.addWidget(self.choose_button)
        layout.addStretch()

        self.update_button_text(self.batch_checkbox.isChecked())
        self.apply_styles()

    def update_button_text(self, batch_enabled: bool):
        self.convert_label.setText(
            "Convert files in the folder to:" if batch_enabled else "Convert file to:"
        )
        self.choose_button.setText("Choose folder" if batch_enabled else "Choose file")

    def apply_styles(self):
        check_icon_path = (self.attributes_dir / "check.png").as_posix()
        arrow_icon_path = (self.attributes_dir / "button_down.png").as_posix()

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: #303030;
            }}

            QLabel {{
                color: white;
                font-size: 13px;
            }}

            QLabel#infoLabel {{
                background-color: transparent;
                color: #B7DDF2;
                border: 1px solid #B7DDF2;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }}

            QLabel#infoLabel:hover {{
                color: white;
                border: 1px solid white;
            }}

            QCheckBox {{
                spacing: 5px;
                color: white;
                font-size: 12px;
            }}

            QCheckBox::indicator {{
                width: 12px;
                height: 12px;
                border: 2px solid #555;
                border-radius: 4px;
                background-color: #2E2E2E;
            }}

            QCheckBox::indicator:hover {{
                background-color: #3C3C3C;
                border: 2px solid #777;
            }}

            QCheckBox::indicator:pressed {{
                background-color: #1E1E1E;
                border: 2px solid #999;
            }}

            QCheckBox::indicator:checked {{
                background-color: #4CAF50;
                border: 2px solid #80E27E;
                image: url("{check_icon_path}");
            }}

            QCheckBox::indicator:checked:hover {{
                background-color: #45A049;
                border: 2px solid #76D275;
            }}

            QComboBox {{
                min-height: 24px;
                background-color: #252525;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 12px;
            }}

            QComboBox QAbstractItemView {{
                background-color: #272727;
                color: white;
                selection-background-color: #555555;
            }}

            QComboBox::drop-down {{
                width: 22px;
                background-color: #444444;
                border-left: 1px solid #555555;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}

            QComboBox::down-arrow {{
                image: url("{arrow_icon_path}");
                width: 12px;
                height: 12px;
            }}

            QPushButton {{
                background-color: #252525;
                color: white;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 0px 14px;
                font-size: 13px;
            }}

            QPushButton:hover {{
                background-color: #3C3C3C;
                border: 2px solid #777;
            }}

            QPushButton:pressed {{
                background-color: #1E1E1E;
                border: 2px solid #999;
            }}
            """
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "attributes" / "ALM.ico")))
    window = ConverterWidget()
    window.show()
    sys.exit(app.exec())
