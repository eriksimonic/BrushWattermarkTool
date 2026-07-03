from PySide6.QtCore import QThread, Signal

from brush_watermark.services.update_check import UpdateCheckResult, check_for_update


class UpdateChecker(QThread):
    completed = Signal(UpdateCheckResult)

    def run(self) -> None:
        self.completed.emit(check_for_update())
