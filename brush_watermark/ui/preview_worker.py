import threading
from dataclasses import dataclass
from typing import Any, Optional

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QThread, Signal

from brush_watermark.services.document import Document, PreviewRequest


@dataclass
class PreviewJob:
    """One preview render: what to draw and how the result is laid out.

    `layout` is opaque to the worker; MainWindow uses it to place the result.
    """

    generation: int
    doc: Document
    request: PreviewRequest
    layout: Any


class PreviewWorker(QThread):
    """Renders canvas previews off the GUI thread, newest request first.

    Holds at most one waiting job: submitting while a render is running
    replaces the waiting job, so a burst of edits (an anchor drag) renders the
    latest state as soon as the current render finishes instead of queueing a
    backlog. Rendering only reads the job's PreviewRequest snapshot; results
    are converted to a QImage here and to a QPixmap on the GUI thread.
    """

    # job, QImage, stroke render time in ms (see Document.render_preview_timed)
    rendered = Signal(object, object, float)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cond = threading.Condition()
        self._pending: Optional[PreviewJob] = None
        self._stopping = False

    def submit(self, job: PreviewJob) -> None:
        with self._cond:
            self._pending = job
            self._cond.notify()

    def stop(self) -> None:
        with self._cond:
            self._stopping = True
            self._pending = None
            self._cond.notify()
        self.wait(3000)

    def run(self) -> None:
        while True:
            with self._cond:
                while self._pending is None and not self._stopping:
                    self._cond.wait()
                if self._stopping:
                    return
                job, self._pending = self._pending, None
            try:
                image, render_ms = job.doc.render_preview_timed(job.request)
                qimage = ImageQt(image.convert("RGBA")).copy()
            except Exception as exc:  # pragma: no cover - surfaced to the UI, not swallowed
                self.failed.emit(str(exc))
                continue
            self.rendered.emit(job, qimage, render_ms)
