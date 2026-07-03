from PySide6.QtCore import QThread, Signal

from brush_watermark.services.auto_update import prepare_and_launch_update


class AutoUpdater(QThread):
    progress = Signal(int, str)
    failed = Signal(str)

    def __init__(self, download_url: str, process_id: int, exe_args: list[str]):
        super().__init__()
        self._download_url = download_url
        self._process_id = process_id
        self._exe_args = exe_args

    def run(self) -> None:
        try:
            prepare_and_launch_update(
                self._download_url,
                process_id=self._process_id,
                exe_args=self._exe_args,
                progress=lambda percent, message: self.progress.emit(percent, message),
            )
        except Exception as exc:
            self.failed.emit(str(exc))
