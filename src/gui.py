import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QTimer, QObject, QEvent, QPoint, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QDialog,
)
from conversion_pipeline import file_conversion

#############################################################
# Main GUI

"""
This class manages main GUI of the software
"""

class ConverterWidget(QWidget):

    #--------------------------------------------------
    # Initialization
    def __init__(self, parent=None):
        super().__init__(parent)
        self.attributes_dir = Path(__file__).resolve().parent / "attributes"
        self.tooltip_manager = CustomToolTipManager(self)
        self.settings = QSettings("i3S", "ALM File Converter")
        self.setup_ui()

    #--------------------------------------------------
    # Algorithm Functions

    def run_single_file_conversion(self):
        """
        Function that handles the conversion of a single microscopy file inside the GUI
        """

        # Verify the user choice for the output file
        output_file_format = self.format_combobox.currentText()

        # Let the user choose the file
        input_file_path = file_conversion.file_choice()

        if input_file_path is None:
            return

        # hide the GUI while the conversion happens
        self.hide()
        QApplication.processEvents()

        # Initialize the single-file conversion algorithm
        try:
            file_conversion.single_file_conversion(output_file_format, input_file_path)
        finally:
            self.restore_window()

    
    def run_single_omezarr_conversion(self):
        """
        Function that handles the conversion of a single OME-Zarr/Zarr file inside the GUI
        """

        # Verify the user choice for the output file
        output_file_format = self.format_combobox.currentText()

        # Let the user choose the file
        input_file_path = file_conversion.zarr_choice()

        if input_file_path is None:
            return

        # hide the GUI while the conversion happens
        self.hide()
        QApplication.processEvents()

        # Initialize the single-file conversion algorithm
        try:
            file_conversion.single_omezarr_conversion(output_file_format, input_file_path)
        finally:
            self.restore_window()


    def run_batch_conversion(self):
        """
        Function that handles the batch conversion inside the GUI
        """

        # Verify the user choice for the output files
        output_file_format = self.format_combobox.currentText()

        # Let the user choose the folder
        input_file_paths, n_files, input_folder = file_conversion.folder_choice(self)

        if input_folder is None:
            return

        # Hide the GUI window while the conversion happens
        self.hide()
        QApplication.processEvents()

        # Initialize the conversion algorithm
        try:
            file_conversion.batch_conversion(output_file_format, input_file_paths, n_files, input_folder)
        finally:
            self.restore_window()

    #--------------------------------------------------
    # UI

    def setup_ui(self):

        #-----------------------------------------
        # Initial setup for the window
        self.setWindowTitle("ALM File Converter")
        self.setWindowIcon(QIcon(str(self.attributes_dir / "ALM.ico")))
        self.setMinimumWidth(280)
        self.setMaximumWidth(280)

        #-----------------------------------------
        # Vertical layout definition
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(9)

        #-----------------------------------------
        # UI Elements

        # Checkbox for the Batch Conversion
        self.batch_checkbox = QCheckBox("Batch Processing")
            # add the setting saving of the checkbox
        batch_enabled = self.settings.value("batch_processing_enabled", True, type=bool)
        self.batch_checkbox.setChecked(batch_enabled)
        self.batch_checkbox.toggled.connect(self.update_button_text)
        self.batch_checkbox.toggled.connect(self.save_batch_setting)

        # Information Label
        self.batch_info_label = QLabel("i")
        self.batch_info_label.setObjectName("infoLabel")
        self.batch_info_label.setFixedSize(16, 16)
        self.batch_info_label.setAlignment(Qt.AlignCenter)
        self.batch_info_label.setCursor(Qt.PointingHandCursor)
        self.batch_info_label.setCursor(Qt.PointingHandCursor)
        self.batch_info_label.mousePressEvent = lambda event: QDesktopServices.openUrl(
            QUrl("https://github.com/synkss/Microscopy_File_Converter")
        )
        self.tooltip_manager.attach_tooltip(
            self.batch_checkbox,
            "Batch processing will convert all files in a folder.\n" \
            "Disable if you want to convert a single file.",
        )
        self.tooltip_manager.attach_tooltip(
            self.batch_info_label,
            "This program currently has support for:\n" \
            ".ims, .lif, .ome.tif, .ome.tiff, .ome.zarr,\n" \
            ".tif, .tiff, .nd2, .zarr.\n" \
            "\n" \
            "To access this project's github for more\n" \
            "information, click this button."

        )

        self.convert_label = QLabel()


        # Create a clickable label
        self.author_label = QLabel("Made by: Simão Seixas, i3S")
        self.author_label.setObjectName("authorLabel")
        self.author_label.setAlignment(Qt.AlignRight)
        self.author_label.setCursor(Qt.PointingHandCursor)
        self.author_label.mousePressEvent = lambda event: QDesktopServices.openUrl(
            QUrl("https://github.com/synkss")
        )

        # Output file format ComboBox
        self.format_combobox = QComboBox()
        self.format_combobox.addItems([".ome.tiff", ".ome.tif", ".ome.zarr", ".tiff", ".tif", ])

        # Batch Procesing Button
        self.choose_button = QPushButton()
        self.choose_button.setFixedHeight(34)
            # Wire the function
        self.choose_button.clicked.connect(self.run_batch_conversion)

        # Single Microscopy File Button
        self.select_file_button = QPushButton("Select Microscopy File")
        self.select_file_button.setFixedHeight(34)
            # Wire the function
        self.select_file_button.clicked.connect(self.run_single_file_conversion)

        # Single Zarr File Button
        self.select_zarr_button = QPushButton("Select OME-Zarr/Zarr File")
        self.select_zarr_button.setFixedHeight(34)
            # Wire the function
        self.select_zarr_button.clicked.connect(self.run_single_omezarr_conversion)

        #-----------------------------------------
        # UI Layout Structure

        batch_row = QHBoxLayout()
        batch_row.setContentsMargins(0, 0, 0, 0)
        batch_row.setSpacing(6)
        batch_row.addWidget(self.batch_checkbox)
        batch_row.addStretch()
        batch_row.addWidget(self.batch_info_label)


        single_input_layout = QVBoxLayout()
        single_input_layout.setContentsMargins(0, 0, 0, 0)
        single_input_layout.setSpacing(7)
        single_input_layout.addWidget(self.select_file_button)
        single_input_layout.addWidget(self.select_zarr_button)
        self.single_input_widget = QWidget()
        self.single_input_widget.setLayout(single_input_layout)
        self.single_input_widget.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Maximum,
        )

        # Construction of the full UI
        layout.addLayout(batch_row)
        layout.addWidget(self.convert_label, alignment=Qt.AlignLeft)
        layout.addWidget(self.format_combobox)
        layout.addWidget(self.choose_button)
        layout.addWidget(self.single_input_widget)
        layout.addStretch()
        layout.addSpacing(5)
        layout.addWidget(self.author_label, alignment=Qt.AlignRight)

        self.update_button_text(self.batch_checkbox.isChecked())
        self.apply_styles()

    #--------------------------------------------------
    # Stylistic Functions

    def restore_window(self):
        """
        Function that makes sure the GUI window is always restored
        """

        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(100, self.raise_)
        QTimer.singleShot(100, self.activateWindow)


    def save_batch_setting(self, checked):
        """
        Updates the checkbox enabled value in the computer settings
        to save it for the next session of the program
        """
        self.settings.setValue("batch_processing_enabled", checked)

    def update_button_text(self, batch_enabled: bool):
        """
        Changes the appearance of the GUI after the enabling/disabling of the checkbox
        """
        self.convert_label.setText(
            "Convert files in the folder to:" if batch_enabled else "Convert file to:"
        )
        self.choose_button.setText("Select folder")
        self.choose_button.setVisible(batch_enabled)
        self.single_input_widget.setVisible(not batch_enabled)
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    def apply_styles(self):
        """
        Applies the initial styling of the GUI
        """
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

            QLabel#authorLabel {{
                color: #9A9A9A;
                font-size: 9px;
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

#############################################################
# Tooltip Manager

"""
This class manages the yellow tooltips
that appear in some parts of the GUI
"""

class CustomToolTipManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tooltip = QLabel(parent)
        self.tooltip.setStyleSheet("""
            QLabel {
                background-color: yellow;
                color: black;
                border: 1px solid black;
                padding: 5px;
                border-radius: 0px;
            }
        """)
        self.tooltip.setWindowFlags(Qt.ToolTip)
        self.tooltip.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.tooltip.hide()

        self._current_widget = None

    def attach_tooltip(self, widget: QWidget, text: str):
        widget.setProperty("custom_tooltip", text)
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        widget.destroyed.connect(self._on_widget_destroyed)

        dlg = self._find_parent_dialog(widget)
        if isinstance(dlg, QDialog):
            try:
                dlg.installEventFilter(self)
                dlg.finished.connect(self.hide_tooltip)
                dlg.accepted.connect(self.hide_tooltip)
                dlg.rejected.connect(self.hide_tooltip)
                dlg.destroyed.connect(self.hide_tooltip)
            except Exception:
                return  # if the dialog is in a weird state, silently skip

    def _on_widget_destroyed(self):
        self.hide_tooltip()
        self._current_widget = None

    def detach_tooltip(self, widget: QWidget):
        widget.removeEventFilter(self)
        widget.setProperty("custom_tooltip", None)
        if widget is self._current_widget:
            self.hide_tooltip()
            self._current_widget = None

    def eventFilter(self, obj, event):
        try:
            et = event.type()

            # 1) Entering a widget: start tracking + show
            if et == QEvent.Enter and isinstance(obj, QWidget):
                text = obj.property("custom_tooltip")
                if text:
                    self._current_widget = obj
                    try:
                        self.show_tooltip(text, event.globalPos())
                    except Exception:
                        return True  # eat the event but do nothing

            # 2) Moving within that same widget: reposition
            elif et == QEvent.MouseMove and obj is self._current_widget:
                if self.tooltip.isVisible():
                    try:
                        self.show_tooltip(obj.property("custom_tooltip"), event.globalPos())
                    except Exception:
                        return True

            # 3) Leaving it: stop & hide
            elif et == QEvent.Leave and obj is self._current_widget:
                self.hide_tooltip()
                self._current_widget = None

            # 4) Dialog close/hide/focus-loss: also hide
            elif et in (QEvent.Hide, QEvent.Close, QEvent.WindowDeactivate) and isinstance(obj, QDialog):
                self.hide_tooltip()
                self._current_widget = None

            # 5) If anything we watch is destroyed: hide
            elif et == QEvent.Destroy:
                self.hide_tooltip()
                self._current_widget = None

        except TypeError:
            # sometimes Qt hands us odd obj/event combos; just ignore
            return False
        except Exception:
            # catch-all so nothing bubbles out
            return False

        return super().eventFilter(obj, event)

    def show_tooltip(self, text: str, pos: QPoint):
        try:
            self.tooltip.setText(text)
            self.tooltip.adjustSize()

            margin = 10
            x = pos.x() + margin
            y = pos.y() - self.tooltip.height() - margin
            self.tooltip.move(x, y)
            self.tooltip.show()
        except Exception:
            # any problem during layout/move/show just abort
            return

    def hide_tooltip(self):
        try:
            if self.tooltip.isVisible():
                self.tooltip.hide()
        except Exception:
            pass

    def _find_parent_dialog(self, widget: QWidget):
        w = widget
        while w is not None:
            if isinstance(w, QDialog):
                return w
            w = w.parent()
        return None
