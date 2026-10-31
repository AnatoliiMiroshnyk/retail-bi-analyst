"""Non-GUI work only. Result is consumed by the GUI after finished()."""
from PySide6.QtCore import QThread
import traceback


class TaskThread(QThread):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.result = None
        self.error = None
        self.traceback_text = ''

    def run(self):
        try:
            self.result = self.task()
        except Exception as error:
            self.error = error
            self.traceback_text = traceback.format_exc()
