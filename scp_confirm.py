"""Marshal owner-approved GUI operations to the Qt thread; never trust a tool argument as approval."""

from concurrent.futures import Future

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QMessageBox

__all__ = ["GuiGate"]


class GuiGate(QObject):
    request = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.request.connect(self.dispatch)

    @Slot(object)
    def dispatch(self, item):
        future, fn = item
        if not future.set_running_or_notify_cancel():
            return
        try:
            future.set_result(fn())
        except Exception as exc:
            future.set_exception(exc)

    def call(self, fn):
        if QThread.currentThread() == self.thread():
            return fn()
        f = Future()
        self.request.emit((f, fn))
        return f.result()

    def confirm(self, name, params):
        return self.call(
            lambda: QMessageBox.question(
                self.parent(),
                "Разрешить действие?",
                name + "\n" + repr(params)[:2000],
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            == QMessageBox.Yes
        )
