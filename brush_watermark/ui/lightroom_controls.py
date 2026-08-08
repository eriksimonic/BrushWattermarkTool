from PySide6.QtCore import Qt, QRect, QRectF, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor, QPainter, QPen

from brush_watermark.ui.design_tokens import (
    ACCENT,
    BORDER,
    ON_ACCENT,
    SLIDER_HANDLE,
    TEXT_SECONDARY,
    TRACK,
)
from brush_watermark.ui.icons import get_icon, get_pixmap


class _HeaderRow(QWidget):
    """Clickable row — used internally by CollapsibleSection."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit()
        event.accept()


class CollapsibleSection(QWidget):
    """A section header with a chevron that expands/collapses a body area.

    Callers add their section content to `body_layout`.
    """

    toggled = Signal(bool)

    CHEVRON_SIZE = 12
    ICON_SIZE = 15

    def __init__(
        self,
        title: str,
        icon_name: str | None = None,
        expanded: bool = True,
        top_divider: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._expanded = expanded

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 10 if top_divider else 0, 0, 8)
        outer.setSpacing(8)

        if top_divider:
            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.HLine)
            divider.setObjectName("SectionDivider")
            outer.addWidget(divider)

        header = _HeaderRow()
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self._chevron_label = QLabel()
        self._chevron_label.setFixedWidth(self.CHEVRON_SIZE)
        header_row.addWidget(self._chevron_label)

        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(get_pixmap(icon_name, self.ICON_SIZE, TEXT_SECONDARY))
            header_row.addWidget(icon_label)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("SectionHeader")
        header_row.addWidget(self._title_label, 1)

        header.clicked.connect(self._toggle)
        outer.addWidget(header)

        self._body = QWidget()
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(0, 2, 0, 0)
        self.body_layout.setSpacing(7)
        outer.addWidget(self._body)

        self._update_chevron()
        self._body.setVisible(self._expanded)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._update_chevron()
        self.toggled.emit(self._expanded)

    def _update_chevron(self):
        name = "chevron-down" if self._expanded else "chevron-right"
        self._chevron_label.setPixmap(get_pixmap(name, self.CHEVRON_SIZE, TEXT_SECONDARY))

    def set_title(self, title: str):
        self._title_label.setText(title)


class BoxCheckBox(QCheckBox):
    """Checkbox with a hollow outer box; checked adds a padded inner fill."""

    INDICATOR_SIZE = 14
    BORDER = 1
    GAP = 3
    RADIUS = 2

    def paintEvent(self, _event):
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

            style = self.style()
            indicator = style.subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, opt, self)
            contents = style.subElementRect(QStyle.SubElement.SE_CheckBoxContents, opt, self)

            ix = int(indicator.x() + (indicator.width() - self.INDICATOR_SIZE) / 2)
            iy = int(indicator.y() + (indicator.height() - self.INDICATOR_SIZE) / 2)

            border = QColor(BORDER)
            if not self.isEnabled():
                border.setAlpha(128)

            painter.setPen(QPen(border, self.BORDER))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                QRectF(ix + 0.5, iy + 0.5, self.INDICATOR_SIZE - 1, self.INDICATOR_SIZE - 1),
                self.RADIUS,
                self.RADIUS,
            )

            if self.isChecked():
                fill = QColor(ACCENT)
                if not self.isEnabled():
                    fill.setAlpha(128)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(fill)
                painter.drawRoundedRect(
                    QRectF(ix + 0.5, iy + 0.5, self.INDICATOR_SIZE - 1, self.INDICATOR_SIZE - 1),
                    self.RADIUS,
                    self.RADIUS,
                )
                check_size = self.INDICATOR_SIZE - 2 * self.GAP
                check_pixmap = get_pixmap("check", check_size, ON_ACCENT)
                cx = ix + (self.INDICATOR_SIZE - check_size) // 2
                cy = iy + (self.INDICATOR_SIZE - check_size) // 2
                if not self.isEnabled():
                    painter.setOpacity(0.5)
                painter.drawPixmap(cx, cy, check_pixmap)
                painter.setOpacity(1.0)

            label_opt = QStyleOptionButton(opt)
            label_opt.rect = contents
            style.drawControl(QStyle.ControlElement.CE_CheckBoxLabel, label_opt, painter, self)
        finally:
            painter.end()


class LightroomSlider(QSlider):
    """Horizontal slider with an off-white circular handle."""

    MARGIN_H = 6
    TRACK_HEIGHT = 2
    HANDLE_RADIUS = 4

    dragStarted = Signal()
    dragEnded = Signal()

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent: QWidget | None = None):
        super().__init__(orientation, parent)
        self.setFixedHeight(18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        width = self.width()
        height = self.height()
        track_y = height // 2
        track_left = self.MARGIN_H
        track_right = width - self.MARGIN_H
        track_width = max(1, track_right - track_left)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(TRACK))
        painter.drawRoundedRect(track_left, track_y - 1, track_width, self.TRACK_HEIGHT, 1, 1)

        span = max(1, self.maximum() - self.minimum())
        ratio = (self.value() - self.minimum()) / span
        handle_center_x = track_left + ratio * track_width

        fill_width = max(0, int(handle_center_x - track_left))
        painter.setBrush(QColor(ACCENT))
        painter.drawRoundedRect(track_left, track_y - 1, fill_width, self.TRACK_HEIGHT, 1, 1)

        painter.setBrush(QColor(SLIDER_HANDLE))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            int(handle_center_x - self.HANDLE_RADIUS),
            int(track_y - self.HANDLE_RADIUS),
            self.HANDLE_RADIUS * 2,
            self.HANDLE_RADIUS * 2,
        )

    def mousePressEvent(self, event):
        self._move_to(event.position().x())
        self.dragStarted.emit()
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._move_to(event.position().x())
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.dragEnded.emit()

    def _move_to(self, x: float):
        track_left = self.MARGIN_H
        track_right = self.width() - self.MARGIN_H
        track_width = max(1, track_right - track_left)
        ratio = max(0.0, min(1.0, (x - track_left) / track_width))
        value = self.minimum() + round(ratio * (self.maximum() - self.minimum()))
        self.setValue(int(value))


class SliderRow(QWidget):
    def __init__(self, name: str, low: int, high: int, value: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.name_label = QLabel(name)
        self.name_label.setObjectName("SliderName")
        self.value_label = QLabel()
        self.value_label.setObjectName("SliderValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        header.addWidget(self.name_label, 1)
        header.addWidget(self.value_label)

        self.slider = LightroomSlider()
        self.slider.setRange(low, high)
        self.slider.setValue(value)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addLayout(header)
        layout.addWidget(self.slider)

    def set_value_text(self, text: str):
        self.value_label.setText(text)
