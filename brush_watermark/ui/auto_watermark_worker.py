from PIL import Image
from PySide6.QtCore import QThread, Signal

from brush_watermark.services.auto_watermark import find_auto_watermark_paths


class AutoWatermarkWorker(QThread):
    """Runs subject/busy-area analysis off the GUI thread.

    Only reads the image; the resulting paths are applied to the Document
    (add_paths_as_strokes) back on the GUI thread by whoever owns
    `completed`, since Document is not safe to mutate from here.
    """

    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, image: Image.Image, density: int, parent=None):
        super().__init__(parent)
        self._image = image
        self._density = density

    def run(self) -> None:
        try:
            paths = find_auto_watermark_paths(self._image, self._density)
        except Exception as exc:  # pragma: no cover - surfaced to the UI, not swallowed
            self.failed.emit(str(exc))
            return
        self.completed.emit(paths)
