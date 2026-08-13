from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QSizePolicy, QWidget

from brush_watermark.ui.design_tokens import ACCENT, DIVIDER

THUMB_SIZE = 64
ITEM_PADDING = 6
STRIP_HEIGHT = THUMB_SIZE + ITEM_PADDING * 2


class _FilmstripItem(QWidget):
    clicked = Signal()

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._active = False
        self._dirty = False
        self.setFixedSize(THUMB_SIZE + ITEM_PADDING * 2, STRIP_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self.update()

    def set_dirty(self, dirty: bool) -> None:
        if dirty != self._dirty:
            self._dirty = dirty
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = (self.width() - self._pixmap.width()) // 2
        y = (self.height() - self._pixmap.height()) // 2
        painter.drawPixmap(x, y, self._pixmap)

        pen = QPen(QColor(ACCENT if self._active else DIVIDER), 2 if self._active else 1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)

        if self._dirty:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(ACCENT))
            painter.drawEllipse(self.width() - 11, 4, 7, 7)
        painter.end()


class FilmstripWidget(QScrollArea):
    """Lightroom-style bottom strip for switching between open images."""

    imageSelected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FilmstripArea")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(STRIP_HEIGHT + 14)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        container = QWidget()
        self._layout = QHBoxLayout(container)
        self._layout.setContentsMargins(8, 7, 8, 7)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)
        self.setWidget(container)

        self._items: list[_FilmstripItem] = []

    def set_thumbnails(self, pixmaps: list) -> None:
        for item in self._items:
            item.setParent(None)
            item.deleteLater()
        self._items = []
        for idx, pixmap in enumerate(pixmaps):
            item = _FilmstripItem(pixmap)
            item.clicked.connect(lambda i=idx: self.imageSelected.emit(i))
            self._layout.insertWidget(idx, item)
            self._items.append(item)

    def set_active_index(self, index: int) -> None:
        for i, item in enumerate(self._items):
            item.set_active(i == index)

    def set_dirty_flags(self, flags: list) -> None:
        for item, dirty in zip(self._items, flags):
            item.set_dirty(dirty)

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y() or event.angleDelta().x()
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - delta)
        event.accept()
