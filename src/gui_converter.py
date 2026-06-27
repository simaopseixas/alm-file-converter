"""
This file builds the main GUI of the program, where the user chooses the conversion parameters.
In this window the output file format and whether the program performs a batch conversion or a single file conversion can be chosen by the user.
Then, after the start of the converison process, this window disappears and the conversion process starts in a new thread.
During the conversion only the logger window remains, displaying information about the conversion.
When the conversion process is done, this window reappears, to allow the user to perform another conversion.
"""

import sys
import os
from pathlib import Path
from PySide6.QtCore import Qt, QSettings, QTimer, QObject, QEvent, QPoint, QUrl, QThread, Signal, Slot
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import  QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QDialog, QFrame
from conversion_pipeline import file_conversion

#############################################################
# Threaded Conversion

class SignalLogger:
    """
    This is a logger adapter that essentially builds a bridge between the conversion
    that happens in a separate thread and the logging that happens in the main one.

    The conversion pipeline expects an object with a "logger.print(...)" method.
    The LoggerWindow class already has that method, but the GUI must stay in the main thread.
    This class gives the worker thread a safe logging object that emits text with information
    about the conversion through a Qt Signal.
    """

    def __init__(self, signal):
        """
        Store the signal that will carry the text to the GUI thread.
        """
        self.signal = signal

    def print(self, *args, sep=" ", end="\n", flush=False):
        """
        Match python's print and emit the message
        """

        text = []

        for arg in args:
            text.append(str(arg))

        message = sep.join(text)
        message += end

        self.signal.emit(message)


class ConversionWorker(QObject):
    """
    This is an object that runs a conversion outside of the main GUI thread.

    In ConverterWidget this object is moved into a QThread when conversion starts.
    It performs the reading/writing process while the Qt event loop remains free
    to write on the logger window.

    It never touches the GUI Qt widgets directly. Communication back to the GUI is done only through signals.
    """

    # Define the signals
    # signal that carries text from the worker thread to the logger window
    log = Signal(str)
    # signal that is used when the conversion ends to restore the main window and clean up the thread
    finished = Signal()

    def __init__(self, conversion_mode, output_file_format, input_file_path=None, input_file_paths=None, n_files=None, input_folder=None, compress_output=False, create_zarr_pyramids=False):
        """
        Store the conversion type and its arguments
        "conversion_mode" can be: "single_file", "single_zarr" or "batch".
        """

        super().__init__()

        # Store the arguments as global variables
        self.conversion_type = conversion_mode
        self.output_file_format = output_file_format
        self.input_file_path = input_file_path
        self.input_file_paths = input_file_paths
        self.n_files = n_files
        self.input_folder = input_folder
        self.compress_output = compress_output
        self.create_zarr_pyramids = create_zarr_pyramids


    @Slot()
    def run(self):
        """
        Runs the selected conversion in a worker thread.
        """

        # start a logger object for the conversion pipeline
        logger = SignalLogger(self.log)

        try:
            # single-file conversion
            if self.conversion_type == "single_file":
                file_conversion.single_file_conversion(
                    self.output_file_format,
                    self.input_file_path,
                    compress_output=self.compress_output,
                    create_zarr_pyramids=self.create_zarr_pyramids,
                    logger=logger
                )

            # single OME-Zarr file conversion
            elif self.conversion_type == "single_zarr":
                file_conversion.single_omezarr_conversion(
                    self.output_file_format,
                    self.input_file_path,
                    compress_output=self.compress_output,
                    create_zarr_pyramids=self.create_zarr_pyramids,
                    logger=logger
                )

            # batch conversion
            elif self.conversion_type == "batch":
                file_conversion.batch_conversion(
                    self.output_file_format, 
                    self.input_file_paths, 
                    self.n_files,
                    self.input_folder,
                    compress_output=self.compress_output,
                    create_zarr_pyramids=self.create_zarr_pyramids,
                    logger=logger
                )

        # always notify the GUI that the worker finished
        finally:
            self.finished.emit()



#############################################################
# Main GUI

class ConverterWidget(QWidget):
    """
    Class that handles the logic and behavior of the main window of the GUI.
    """


    def __init__(self, logger=None, parent=None):
        """
        Function that stars the GUI on initialization
        """

        super().__init__(parent)

        # logger object
        self.logger = logger
        # synchronization flag
        self.syncing_window_state = False
        # conversion running flag
        self.conversion_running = False

        self.attributes_dir = Path(__file__).resolve().parent / "attributes"
        self.tooltip_manager = CustomToolTipManager(self)
        self.settings = QSettings("i3S", "ALM File Converter")
        self.setup_ui()

    def closeEvent(self, event):
        """
        Function that handles the closing of the program
        """

        # logic to cancel a conversion and close the program
        if self.conversion_running:
            if self.logger is not None:
                self.logger.print()
                self.logger.print("Stopping conversion and closing...")

            QTimer.singleShot(2000, lambda: os._exit(0))
            event.ignore()
            return

        # normal logic to close the program without any conversion happening
        if self.logger is not None:
            self.logger.close_from_main_window()

        event.accept()

    def changeEvent(self, event):
        """
        Function that keeps the logger tied to the main window.
        When the main window is minimized or brought to display, it also happens to the logger.
        """

        super().changeEvent(event)

        # If there is no logger do nothing
        if self.logger is None:
            return
        
        # If there is a conversion running, do nothing
        if self.conversion_running:
            return
        
        # Only react to window minimize / restore state changes
        if event.type() != QEvent.Type.WindowStateChange:
            return
        
        # Ignore state changes caused by the other window synchronizing
        if self.syncing_window_state:
            return
        
        # Mark both windows as syncing to avoid recursive minimize / restore events
        self.syncing_window_state = True
        self.logger.syncing_window_state = True

        try:
            # Minimize the main window together with the logger
            if self.isMinimized():
                self.logger.showMinimized()

            # Restore the main window when the logger is restored
            else:
                if self.logger.isMinimized():
                    self.logger.showNormal()
                self.logger.raise_()

        # Always clear the sync flags
        finally:
            self.syncing_window_state = False
            self.logger.syncing_window_state = False

    #--------------------------------------------------
    # Algorithm Functions

    def conversion_finished(self):
        """
        Function that runs when the conversion worker finishes.
        """

        self.restore_window()
        self.conversion_running = False

    def start_conversion_worker(self, conversion_mode, output_file_format, input_file_path=None, input_file_paths=None, n_files=None, input_folder=None):
        """
        Function that starts the conversion in a separate thread
        """

        # make the conversion running flag go True
        self.conversion_running = True

        # create the thread object
        self.conversion_thread = QThread(self)
        
        # get the chosen compression boolean
        compress_output = self.compress_output_checkbox.isChecked()

        # get the chosen pyramid boolean
        create_zarr_pyramids = (self.format_combobox.currentText() == ".ome.zarr" and self.zarr_pyramids_checkbox.isChecked() )

        # create the worker object
        self.conversion_worker = ConversionWorker(
            conversion_mode,
            output_file_format,
            input_file_path=input_file_path,
            input_file_paths=input_file_paths,
            n_files=n_files,
            input_folder=input_folder,
            compress_output=compress_output,
            create_zarr_pyramids=create_zarr_pyramids,
        )

        # move the worker into the new thread
        self.conversion_worker.moveToThread(self.conversion_thread)
        # when the thread starts, run the conversion
        self.conversion_thread.started.connect(self.conversion_worker.run)
        # send worker messages to the logger window
        self.conversion_worker.log.connect(self.logger.append_text, Qt.QueuedConnection)
        # stop the thread when the conversion finishes
        self.conversion_worker.finished.connect(self.conversion_thread.quit)
        # delete the worker after the conversion finishes
        self.conversion_worker.finished.connect(self.conversion_worker.deleteLater)
        # delete the thread after the conversion finishes
        self.conversion_thread.finished.connect(self.conversion_thread.deleteLater)
        # end the process in the worker by running the conversion finished function
        self.conversion_worker.finished.connect(self.conversion_finished)

        # start the thread
        self.conversion_thread.start()

    def run_single_file_conversion(self):
        """
        Function that handles the conversion of a single microscopy file inside the GUI
        """

        # Verify the user choice for the output file
        output_file_format = self.format_combobox.currentText()

        # Let the user choose the file
        input_file_path = file_conversion.file_choice(logger=self.logger)

        if input_file_path is None:
            return
        
        # Hide the main window of the GUI
        self.hide()
        QApplication.processEvents()

        # Initialize the single-file conversion algorithm
        self.start_conversion_worker("single_file", output_file_format, input_file_path=input_file_path)

    
    def run_single_omezarr_conversion(self):
        """
        Function that handles the conversion of a single OME-Zarr file inside the GUI
        """

        # Verify the user choice for the output file
        output_file_format = self.format_combobox.currentText()

        # Let the user choose the file
        input_file_path = file_conversion.zarr_choice(logger=self.logger)

        if input_file_path is None:
            return
        
        # Hide the main window of the GUI
        self.hide()
        QApplication.processEvents()

        # Initialize the single-file conversion algorithm
        self.start_conversion_worker("single_zarr", output_file_format, input_file_path=input_file_path)


    def run_batch_conversion(self):
        """
        Function that handles the batch conversion inside the GUI
        """

        # Verify the user choice for the output files
        output_file_format = self.format_combobox.currentText()

        # Let the user choose the folder
        input_file_paths, n_files, input_folder = file_conversion.folder_choice(self, logger=self.logger)

        if input_folder is None:
            return

        # Hide the main window of the GUI
        self.hide()
        QApplication.processEvents()

        # Initialize the conversion algorithm
        self.start_conversion_worker("batch", output_file_format, input_file_paths=input_file_paths, n_files=n_files, input_folder=input_folder)


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
            QUrl("https://github.com/simaopseixas/alm-file-converter")
        )
        self.tooltip_manager.attach_tooltip(
            self.batch_checkbox,
            "Batch processing will convert all files in a folder.\n" \
            "Disable if you want to convert a single file.",
        )
        self.tooltip_manager.attach_tooltip(
            self.batch_info_label,
            "This program has reading support for:\n" \
            "TIF, TIFF, OME-TIF, OME-TIFF, ICS2,\n" \
            "OME-Zarr, IMS, LIF, ND2, ZVI.\n" \
            "\n" \
            "To access this project's github for more\n" \
            "information, click this button."

        )

        # Checkbox for output compression
        self.compress_output_checkbox = QCheckBox("Compress output files")
        # get the last used state
        last_compression_checkbox_state = self.settings.value("compress_output_enabled", False, type=bool)
        self.compress_output_checkbox.setChecked(last_compression_checkbox_state)
        self.compress_output_checkbox.toggled.connect(self.save_compress_output_setting)
        # add a tooltip
        self.tooltip_manager.attach_tooltip(
            self.compress_output_checkbox,
            "Creates smaller output files, but conversion may take longer." \
        )

        # Checkbox for OME-ZARR pyramids creation
        self.zarr_pyramids_checkbox = QCheckBox("OME-Zarr pyramid levels")
        last_zarr_pyramids_checkbox_state = self.settings.value("zarr_pyramids_enabled", False, type=bool)
        self.zarr_pyramids_checkbox.setChecked(last_zarr_pyramids_checkbox_state)
        self.zarr_pyramids_checkbox.toggled.connect(self.save_zarr_pyramids_setting)
        self.zarr_pyramids_checkbox.setVisible(False)
        # add a tooltip
        self.tooltip_manager.attach_tooltip(
            self.zarr_pyramids_checkbox,
            "Adds downsampled pyramid levels to the output OME-Zarr.\n" \
            "This will increase conversion time and output size." \
        )

        # Separator line
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.HLine)
        separator_line.setFrameShadow(QFrame.Sunken)
        separator_line.setObjectName("separatorLine")

        # simple label text
        self.convert_label = QLabel()

        # Create a clickable label
        self.author_label = QLabel("Made by: Simão Seixas, i3S")
        self.author_label.setObjectName("authorLabel")
        self.author_label.setAlignment(Qt.AlignRight)
        self.author_label.setCursor(Qt.PointingHandCursor)
        self.author_label.mousePressEvent = lambda event: QDesktopServices.openUrl(
            QUrl("https://github.com/simaopseixas")
        )

        # Output file format ComboBox
        self.format_combobox = QComboBox()
        self.format_combobox.addItems([".ome.tiff", ".ome.tif", ".ome.zarr", ".tiff", ".tif", ])
            # Save the last used format as as setting
        last_format = self.settings.value("output_file_format", ".ome.tiff", type=str)
        self.format_combobox.setCurrentText(last_format)
        self.format_combobox.currentTextChanged.connect(self.save_format_setting)
        # connect the checkbox to the update function
        self.format_combobox.currentTextChanged.connect(self.update_zarr_pyramids_visibility)

        # Batch Procesing Button
        self.choose_button = QPushButton()
        self.choose_button.setFixedHeight(34)
            # Wire the function
        self.choose_button.clicked.connect(self.run_batch_conversion)

        # Single Microscopy File Button
        self.select_file_button = QPushButton("Select Input Microscopy File")
        self.select_file_button.setFixedHeight(34)
            # Wire the function
        self.select_file_button.clicked.connect(self.run_single_file_conversion)

        # Single Zarr File Button
        self.select_zarr_button = QPushButton("Select Input OME-Zarr File")
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
        layout.addWidget(self.compress_output_checkbox, alignment=Qt.AlignLeft)
        layout.addWidget(self.zarr_pyramids_checkbox, alignment=Qt.AlignLeft)
        layout.addWidget(separator_line)
        layout.addWidget(self.convert_label, alignment=Qt.AlignLeft)
        layout.addWidget(self.format_combobox)
        layout.addWidget(self.choose_button)
        layout.addWidget(self.single_input_widget)
        layout.addStretch()
        layout.addSpacing(5)
        layout.addWidget(self.author_label, alignment=Qt.AlignRight)

        self.apply_styles()
        self.update_button_text(self.batch_checkbox.isChecked())
        self.update_zarr_pyramids_visibility(self.format_combobox.currentText())
        

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

    def save_compress_output_setting(self, checked):
        """
        Saves whether output compression is enabled.
        """

        self.settings.setValue("compress_output_enabled", checked)


    def save_zarr_pyramids_setting(self, checked):
        """
        Saves whether OME-Zarr pyramid creation is enabled.
        """

        self.settings.setValue("zarr_pyramids_enabled", checked)

    def save_format_setting(self, output_file_format):
        """
        Updates the output file format combo-box value as a setting in the computer
        to be saved for the next session
        """
        self.settings.setValue("output_file_format", output_file_format)

    def update_button_text(self, batch_enabled: bool):
        """
        Changes the appearance of the GUI after the enabling/disabling of the checkbox
        """
        self.convert_label.setText(
            "Convert files in the folder to:" if batch_enabled else "Convert file to:"
        )
        self.choose_button.setText("Select Input Folder")
        self.choose_button.setVisible(batch_enabled)
        self.single_input_widget.setVisible(not batch_enabled)
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    def update_zarr_pyramids_visibility(self, output_file_format=None):
        """
        Shows the OME-Zarr pyramid checkbox only when .ome.zarr is selected as the output file format
        """

        # get the current file format that was chosen in the checkbox
        if output_file_format is None:
            output_file_format = self.format_combobox.currentText()

        # check if the file format corresponds to OME-Zarr
        is_omezarr = True if output_file_format == ".ome.zarr" else False

        self.zarr_pyramids_checkbox.setVisible(is_omezarr)

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
                font-size: 10pt;
            }}

            QLabel#infoLabel {{
                background-color: transparent;
                color: #B7DDF2;
                border: 1px solid #B7DDF2;
                border-radius: 8px;
                font-size: 8pt;
                font-weight: bold;
            }}

            QLabel#infoLabel:hover {{
                color: white;
                border: 1px solid white;
            }}

            QLabel#authorLabel {{
                color: #9A9A9A;
                font-size: 7pt;
            }}


            QCheckBox {{
                spacing: 5px;
                color: white;
                font-size: 9pt;
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
                font-size: 9pt;
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
                font-size: 10pt;
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
        """
        Class initialization function
        """

        super().__init__(parent)

        # QLabel used as the visible tooltip window
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

        # Make the label behave like a tooltip window and ignore mouse events
        self.tooltip.setWindowFlags(Qt.ToolTip)
        self.tooltip.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.tooltip.hide()

        # Tracks which widget is currently showing a tooltip
        self._current_widget = None

    def attach_tooltip(self, widget: QWidget, text: str):
        """
        Attach custom tooltip text to a widget and start watching its mouse events
        """

        widget.setProperty("custom_tooltip", text)
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        widget.destroyed.connect(self._on_widget_destroyed)

        # If the widget lives inside a dialog, also hide the tooltip when the
        # dialog closes, hides, or loses focus
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
        """
        Clear tooltip state when a watched widget is destroyed
        """

        self.hide_tooltip()
        self._current_widget = None


    def detach_tooltip(self, widget: QWidget):
        """
        Remove the custom tooltip behavior from a widget
        """

        widget.removeEventFilter(self)
        widget.setProperty("custom_tooltip", None)

        if widget is self._current_widget:
            self.hide_tooltip()
            self._current_widget = None


    def eventFilter(self, obj, event):
        """
        Watches registered widgets and dialogs to show, move, or hide the tooltip
        """
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
        """
        Update tooltip text and position it slightly above/right of the mouse cursor
        """

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
        """
        Hide the tooltip if it is currently visible
        """

        try:
            if self.tooltip.isVisible():
                self.tooltip.hide()

        except Exception:
            pass


    def _find_parent_dialog(self, widget: QWidget):
        """
        Walk up the parent chain and return the containing dialog, if one exists
        """

        w = widget

        while w is not None:
            if isinstance(w, QDialog):
                return w
            
            w = w.parent()
            
        return None