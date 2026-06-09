"""
This file builds one of the windows of the GUI.
In this window, the Logger Window, some messages about the conversions that are happening are displayed for the user.
It does this by employing a "print" function that can be used in the rest of the code that writes into the window.
"""

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtGui import QTextCursor, QFont

#######################################################################
# Logger Class
class LoggerWindow(QWidget):

    # Message Signal
    message_received = Signal(str)

    def __init__(self):
        """
        Function that runs first when the logger is initialized
        """

        super().__init__()

        # Closing flag
        self.allow_close = False
        # Main window variable
        self.main_window = None
        # Synchronization flag
        self.syncing_window_state = False


        # Window title
        self.setWindowTitle("ALM File Converter")

        self.setWindowFlags(
            Qt.Window |
            Qt.CustomizeWindowHint |
            Qt.WindowTitleHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowCloseButtonHint
        )

        self.text_box = QPlainTextEdit()
        self.text_box.setReadOnly(True)

        font = QFont("Consolas")
        font.setFamilies(["Consolas", "Menlo", "Monaco", "Courier New"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(10)
        self.text_box.setFont(font)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text_box)

        self.message_received.connect(self.append_text)



    #------------------------------------------------------
    # Behavioral functions

    def closeEvent(self, event):
        """
        Function that runs when the logger is closed
        """

        if self.allow_close:
            event.accept()
            return

        if self.main_window is not None:
            if self.main_window.close():
                event.accept()
            else:
                event.ignore()
            return

        event.accept()


    def changeEvent(self, event):
        """
        Function that keeps the main window tied to the logger.
        When the logger is minimized or brought to display, it also happens to the main window.
        """

        super().changeEvent(event)

        # If there is no main window do nothing
        if self.main_window is None:
            return
        
        # Keep the main window hidden while a conversion is running
        if self.main_window.conversion_running:
            return
        
        # Only react to window minimize / restore state changes
        if event.type() != QEvent.Type.WindowStateChange:
            return
        
        # Ignore state changes caused by the other window synchronizing
        if self.syncing_window_state:
            return
        
        # Mark both windows as syncing to avoid recursive minimize / restore events
        self.syncing_window_state = True
        self.main_window.syncing_window_state = True

        try:
            # Minimize the main window together with the logger
            if self.isMinimized():
                self.main_window.showMinimized()

            # Restore the main window when the logger is restored
            else:
                self.main_window.showNormal()
                self.main_window.raise_()

        # Always clear the sync flags
        finally:
            self.syncing_window_state = False
            self.main_window.syncing_window_state = False


    def set_main_window(self, main_window):
        """
        Function that initializes the main window object
        """
        self.main_window = main_window


    def print(self, *args, sep=" ", end="\n", flush=False):
        """
        Function that writes in the logger the intended message
        """

        text = sep.join(str(arg) for arg in args) + end
        self.message_received.emit(text)

    def append_text(self, text):

        self.text_box.moveCursor(QTextCursor.MoveOperation.End)
        self.text_box.insertPlainText(text)
        self.text_box.ensureCursorVisible()


    def close_from_main_window(self):
        """
        Function that handles the closing of the logger when the main window is closed
        """

        self.allow_close = True
        self.close()

    def initial_print(self):

        self.print()
        self.print()
        self.print()
        self.print()
        self.print()
        self.print("                                                                                                                                                 ")
        self.print("                             ###    ##       ##     ##        #######  ##  ##       ######                                                       ")
        self.print("                            ## ##   ##       ###   ###        ##       ##  ##       ##                                                           ")
        self.print("                           ##   ##  ##       #### ####        ######   ##  ##       ######                                                       ")
        self.print("                           #######  ##       ## ### ##        ##       ##  ##       ##                                                           ")
        self.print("                           ##   ##  #######  ##  #  ##        ##       ##  #######  ######                                                       ")
        self.print("                                                                                                                                                 ")
        self.print("                                        ######  #######  ##   ##  ##   ##  #######  ######   ########  ######  ######                            ")
        self.print("                                        ##      ##   ##  ###  ##  ##   ##  ##       ##   ##     ##     ##      ##   ##                           ")
        self.print("                                        ##      ##   ##  #### ##  ##   ##  ######   ######      ##     ######  ######                            ")
        self.print("                                        ##      ##   ##  ## ####   ## ##   ##       ##   ##     ##     ##      ##   ##                           ")
        self.print("                                        ######  #######  ##  ###    ###    #######  ##   ##     ##     ######  ##   ##                           ")
        self.print("                                                                                                                                                 ")
        self.print()
        self.print()
        self.print()
        self.print()
        self.print()
