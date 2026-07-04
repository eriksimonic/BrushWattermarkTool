from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from brush_watermark.ui.design_tokens import SLIDER_HANDLE, TRACK


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

        right = QFrame()
        right.setFrameShape(QFrame.Shape.HLine)
        right.setObjectName("SectionDivider")

        row.addWidget(left, 1)
        row.addWidget(label)
        row.addWidget(right, 1)


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
