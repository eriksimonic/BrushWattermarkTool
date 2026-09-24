"""Bottom strip for switching between open images (shown with 2+ images)."""

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from brush_watermark.ui.app_fonts import mono_font
from brush_watermark.ui.design_tokens import (
    ACCENT_BRIGHT,
    ACCENT_TEXT,
    BORDER,
    BORDER_HOVER,
    SHADOW,
    TEXT,
    TEXT_SECONDARY,
    WARNING,
)
from brush_watermark.ui.icons import get_icon, get_pixmap

THUMB_W = 98
THUMB_H = 66
RING = 4  # room around each thumbnail for the active ring
FILMSTRIP_HEIGHT = 100


class _FilmstripItem(QWidget):
    clicked = Signal()

    def __init__(self, pixmap, number: int, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._number = number
        self._active = False
        self._dirty = False
        self._hover = False
        self.setFixedSize(THUMB_W + 2 * RING, THUMB_H + 2 * RING)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Image {number}")

    def set_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self.update()

    def set_dirty(self, dirty: bool) -> None:
        if dirty != self._dirty:
            self._dirty = dirty
            self.setToolTip(f"Image {self._number}" + (" · unsaved changes" if dirty else ""))
            self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _badge_brush(self) -> QColor:
        color = QColor(SHADOW)
        color.setAlphaF(0.7)
        return color

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        thumb = QRectF(RING, RING, THUMB_W, THUMB_H)

        clip = QPainterPath()
        clip.addRoundedRect(thumb, 8, 8)
        painter.save()
        painter.setClipPath(clip)
        ratio = self._pixmap.devicePixelRatio() or 1.0
        pw, ph = self._pixmap.width() / ratio, self._pixmap.height() / ratio
        painter.drawPixmap(int(RING + (THUMB_W - pw) / 2), int(RING + (THUMB_H - ph) / 2), self._pixmap)
        painter.restore()

        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._active:
            painter.setPen(QPen(QColor(ACCENT_BRIGHT), 2))
            painter.drawRoundedRect(thumb.adjusted(-2, -2, 2, 2), 10, 10)
        else:
            painter.setPen(QPen(QColor(BORDER_HOVER if self._hover else BORDER), 1))
            painter.drawRoundedRect(thumb.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._badge_brush())
        label = str(self._number)
        badge = QRectF(RING + 4, RING + THUMB_H - 20, 16 if len(label) < 2 else 22, 16)
        painter.drawRoundedRect(badge, 4, 4)
        painter.setPen(QColor(TEXT))
        painter.setFont(mono_font(10))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)

        if self._dirty:
            dot_badge = QRectF(RING + THUMB_W - 20, RING + 4, 16, 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._badge_brush())
            painter.drawRoundedRect(dot_badge, 4, 4)
            painter.setBrush(QColor(WARNING))
            painter.drawEllipse(dot_badge.center(), 3, 3)
        painter.end()


class FilmstripWidget(QFrame):
    """Images title plus a horizontally scrolling row of thumbnails."""

    imageSelected = Signal(int)
    previousRequested = Signal()
    nextRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Filmstrip")
        self.setFixedHeight(FILMSTRIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(14)

        title = QWidget()
        title.setFixedWidth(92)
        title_column = QVBoxLayout(title)
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(6)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(7)
        icon = QLabel()
        icon.setPixmap(get_pixmap("images", 14, ACCENT_TEXT))
        text = QLabel("Images")
        text.setObjectName("FilmstripTitle")
        title_row.addWidget(icon)
        title_row.addWidget(text)
        title_row.addStretch(1)
        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)
        nav_row.setSpacing(2)
        self.prev_button = self._nav_button("chevron-left", "Previous image (Ctrl+Left)")
        self.next_button = self._nav_button("chevron-right", "Next image (Ctrl+Right)")
        nav_row.addWidget(self.prev_button)
        nav_row.addWidget(self.next_button)
        nav_row.addStretch(1)
        title_column.addStretch(1)
        title_column.addLayout(title_row)
        title_column.addLayout(nav_row)
        title_column.addStretch(1)
        row.addWidget(title)
        self.prev_button.clicked.connect(lambda _checked=False: self.previousRequested.emit())
        self.next_button.clicked.connect(lambda _checked=False: self.nextRequested.emit())

        self._scroll = QScrollArea()
        self._scroll.setObjectName("FilmstripScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("FilmstripItems")
        self._layout = QHBoxLayout(container)
        self._layout.setContentsMargins(4, 0, 4, 0)
        self._layout.setSpacing(10)
        self._layout.addStretch(1)
        self._scroll.setWidget(container)
        row.addWidget(self._scroll, 1)

        self._items: list[_FilmstripItem] = []

    @staticmethod
    def _nav_button(icon_name: str, tip: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("IconButton")
        button.setFixedSize(30, 30)
        button.setIcon(get_icon(icon_name, 15, TEXT_SECONDARY))
        button.setIconSize(QSize(15, 15))
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def items(self) -> list[_FilmstripItem]:
        return list(self._items)

    def set_thumbnails(self, pixmaps: list) -> None:
        for item in self._items:
            item.setParent(None)
            item.deleteLater()
        self._items = []
        for idx, pixmap in enumerate(pixmaps):
            item = _FilmstripItem(pixmap, idx + 1)
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
        bar = self._scroll.horizontalScrollBar()
        bar.setValue(bar.value() - delta)
        event.accept()
