from PySide6.QtCore    import QObject, QEvent, QPoint, Qt
from PySide6.QtWidgets import QLabel, QWidget, QDialog

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
