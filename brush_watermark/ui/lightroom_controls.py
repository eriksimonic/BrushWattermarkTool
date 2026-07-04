from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
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

from brush_watermark.ui.design_tokens import BORDER, HANDLE, SLIDER_HANDLE, TRACK


class SectionHeader(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 6, 0, 4)
        row.setSpacing(8)

        left = QFrame()
        left.setFrameShape(QFrame.Shape.HLine)
        left.setObjectName("SectionDivider")

        label = QLabel(title)
        label.setObjectName("SectionHeader")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label = label

        right = QFrame()
        right.setFrameShape(QFrame.Shape.HLine)
        right.setObjectName("SectionDivider")

        row.addWidget(left, 1)
        row.addWidget(label)
        row.addWidget(right, 1)

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
            inner_offset = self.BORDER + self.GAP
            inner_size = self.INDICATOR_SIZE - 2 * inner_offset

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
                fill = QColor(HANDLE)
                if not self.isEnabled():
                    fill.setAlpha(128)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(fill)
                painter.drawRect(
                    QRect(ix + inner_offset, iy + inner_offset, inner_size, inner_size)
                )

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
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._move_to(event.position().x())
        event.accept()

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
