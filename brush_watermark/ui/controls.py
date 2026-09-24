"""Shared custom controls for the redesigned UI (see ui/DESIGN.md).

Painted where QSS can't match the design (switch, slider); everything else is
a plain widget styled by object name in styles.py.
"""

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from brush_watermark.ui.design_tokens import (
    ACCENT,
    ACCENT_BRIGHT,
    ACCENT_TEXT,
    BORDER_STRONG,
    ON_ACCENT,
    SLIDER_THUMB,
    SWITCH_OFF,
    TEXT,
    TEXT_LABEL,
    TEXT_MUTED,
)
from brush_watermark.ui.icons import get_icon, get_icon_checkable, get_pixmap


def make_menu(parent: QWidget | None = None) -> QMenu:
    """QMenu that can show the stylesheet's rounded corners (frameless + translucent)."""
    menu = QMenu(parent)
    menu.setWindowFlags(
        menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    return menu


class _ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)


class ToggleSwitch(QAbstractButton):
    """30×18 pill switch: grey track when off, accent track with the knob slid right when on."""

    WIDTH = 30
    HEIGHT = 18
    KNOB = 14

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

    def sizeHint(self) -> QSize:
        return QSize(self.WIDTH, self.HEIGHT)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ACCENT if self.isChecked() else SWITCH_OFF))
        radius = self.HEIGHT / 2
        painter.drawRoundedRect(QRectF(0, 0, self.WIDTH, self.HEIGHT), radius, radius)
        knob_x = 2 + (self.WIDTH - self.KNOB - 4 if self.isChecked() else 0)
        painter.setBrush(QColor(TEXT))
        painter.drawEllipse(QRectF(knob_x, 2, self.KNOB, self.KNOB))
        painter.end()


class SwitchRow(QWidget):
    """Label plus ToggleSwitch; clicking the label toggles too. Mirrors QCheckBox's API."""

    toggled = Signal(bool)

    def __init__(
        self,
        text: str,
        checked: bool = False,
        parent: QWidget | None = None,
        *,
        switch_first: bool = False,
    ):
        super().__init__(parent)
        self.label = _ClickableLabel(text)
        self.label.setObjectName("SwitchLabel")
        self.switch = ToggleSwitch()
        self.switch.setChecked(checked)
        self.switch.setAccessibleName(text)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        if switch_first:
            row.addWidget(self.switch)
            row.addWidget(self.label, 1)
        else:
            row.addWidget(self.label, 1)
            row.addWidget(self.switch)
        self.setFixedHeight(28)

        self.label.clicked.connect(self.switch.toggle)
        self.switch.toggled.connect(self.toggled.emit)

    def isChecked(self) -> bool:
        return self.switch.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.switch.setChecked(checked)


class AccentSlider(QSlider):
    """Horizontal slider: 4 px track, bright-accent fill, white thumb with an accent ring."""

    MARGIN_H = 10
    TRACK_HEIGHT = 4
    THUMB_RADIUS = 7
    RING = 3

    dragStarted = Signal()
    dragEnded = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setFixedHeight(20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _track(self) -> tuple[float, float]:
        return float(self.MARGIN_H), float(max(1, self.width() - 2 * self.MARGIN_H))

    def value_to_x(self, value: int) -> float:
        left, width = self._track()
        span = max(1, self.maximum() - self.minimum())
        return left + (value - self.minimum()) / span * width

    def x_to_value(self, x: float) -> int:
        left, width = self._track()
        ratio = max(0.0, min(1.0, (x - left) / width))
        return int(self.minimum() + round(ratio * (self.maximum() - self.minimum())))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self.isEnabled():
            painter.setOpacity(0.35)
        left, width = self._track()
        mid_y = self.height() / 2
        track = QRectF(left, mid_y - self.TRACK_HEIGHT / 2, width, self.TRACK_HEIGHT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(BORDER_STRONG))
        painter.drawRoundedRect(track, 2, 2)

        thumb_x = self.value_to_x(self.value())
        painter.setBrush(QColor(ACCENT_BRIGHT))
        painter.drawRoundedRect(QRectF(left, track.y(), thumb_x - left, self.TRACK_HEIGHT), 2, 2)

        outer = self.THUMB_RADIUS + self.RING
        painter.setBrush(QColor(ACCENT))
        painter.drawEllipse(QRectF(thumb_x - outer, mid_y - outer, outer * 2, outer * 2))
        painter.setBrush(QColor(SLIDER_THUMB))
        r = self.THUMB_RADIUS
        painter.drawEllipse(QRectF(thumb_x - r, mid_y - r, r * 2, r * 2))
        painter.end()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            return
        self.setValue(self.x_to_value(event.position().x()))
        self.dragStarted.emit()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.isEnabled() and event.buttons() & Qt.MouseButton.LeftButton:
            self.setValue(self.x_to_value(event.position().x()))
        event.accept()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.dragEnded.emit()


class SliderRow(QWidget):
    """Name left, value right (mono), full-width AccentSlider below."""

    def __init__(self, name: str, low: int, high: int, value: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.name_label = QLabel(name)
        self.name_label.setObjectName("SliderName")
        self.value_label = QLabel()
        self.value_label.setObjectName("SliderValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._header = QHBoxLayout()
        self._header.setContentsMargins(0, 0, 0, 0)
        self._header.setSpacing(8)
        self._header.addWidget(self.name_label)
        self._header.addStretch(1)
        self._header.addWidget(self.value_label)

        self.slider = AccentSlider()
        self.slider.setRange(low, high)
        self.slider.setValue(value)
        self.slider.setAccessibleName(name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(self._header)
        layout.addWidget(self.slider)

    def set_value_text(self, text: str) -> None:
        self.value_label.setText(text)

    def add_header_widget(self, widget: QWidget) -> None:
        """Insert a widget (e.g. an Auto chip) just left of the value."""
        self._header.insertWidget(self._header.indexOf(self.value_label), widget)


class SegmentedControl(QFrame):
    """Exclusive pill of buttons, e.g. Original | Watermarked."""

    currentChanged = Signal(int)

    def __init__(self, labels: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SegmentedControl")
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for index, text in enumerate(labels):
            button = QPushButton(text)
            button.setObjectName("Segment")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self._group.addButton(button, index)
            row.addWidget(button)
        self._group.button(0).setChecked(True)
        self._group.idToggled.connect(self._on_toggled)

    def _on_toggled(self, index: int, checked: bool) -> None:
        if checked:
            self.currentChanged.emit(index)

    def currentIndex(self) -> int:
        return self._group.checkedId()

    def setCurrentIndex(self, index: int) -> None:
        self._group.button(index).setChecked(True)


class Chip(QPushButton):
    """Small checkable pill (e.g. the Strength "Auto" toggle)."""

    def __init__(self, text: str, icon_name: str | None = None, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("Chip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            self.setIcon(get_icon_checkable(icon_name, 11, TEXT_LABEL, ACCENT_TEXT))
            self.setIconSize(QSize(11, 11))


class KeyBadge(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("KeyBadge")


class KeyCombo(QWidget):
    """``"Alt+Wheel"`` → [Alt] + [Wheel]."""

    def __init__(self, keys: str, parent: QWidget | None = None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(3)
        for index, part in enumerate(keys.split("+")):
            if index:
                plus = QLabel("+")
                plus.setObjectName("HintText")
                row.addWidget(plus)
            row.addWidget(KeyBadge(part))


class KeyHint(QWidget):
    """Key badges followed by a short description, e.g. [Wheel] Strength."""

    def __init__(self, keys: str, text: str, text_object_name: str = "HintText", parent: QWidget | None = None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(KeyCombo(keys))
        label = QLabel(text)
        label.setObjectName(text_object_name)
        row.addWidget(label)


class Stepper(QFrame):
    """[−] gap 5 [+] integer stepper."""

    valueChanged = Signal(int)

    def __init__(self, low: int, high: int, value: int, prefix: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Stepper")
        self._low, self._high, self._prefix = low, high, prefix
        self._value = max(low, min(high, int(value)))

        self._minus = QPushButton()
        self._plus = QPushButton()
        for button, icon, name in ((self._minus, "minus", "Decrease"), (self._plus, "plus", "Increase")):
            button.setObjectName("StepButton")
            button.setIcon(get_icon(icon, 12, TEXT_LABEL))
            button.setIconSize(QSize(12, 12))
            button.setFixedSize(26, 30)
            button.setAccessibleName(name)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._label = QLabel()
        self._label.setObjectName("StepperValue")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setMinimumWidth(44)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self._minus)
        row.addWidget(self._label)
        row.addWidget(self._plus)

        self._minus.clicked.connect(lambda _checked=False: self.setValue(self._value - 1))
        self._plus.clicked.connect(lambda _checked=False: self.setValue(self._value + 1))
        self._refresh()

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:
        value = max(self._low, min(self._high, int(value)))
        if value == self._value:
            self._refresh()
            return
        self._value = value
        self._refresh()
        self.valueChanged.emit(value)

    def _refresh(self) -> None:
        self._label.setText(f"{self._prefix} {self._value}".strip())
        self._minus.setEnabled(self._value > self._low)
        self._plus.setEnabled(self._value < self._high)


class SplitButton(QWidget):
    """Primary button with a chevron that opens a right-aligned menu."""

    clicked = Signal()

    def __init__(self, text: str, icon_name: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.main = QPushButton(text)
        self.main.setObjectName("SplitMain")
        if icon_name:
            self.main.setIcon(get_icon(icon_name, 15, ON_ACCENT))
            self.main.setIconSize(QSize(15, 15))
        self.arrow = QPushButton()
        self.arrow.setObjectName("SplitArrow")
        self.arrow.setIcon(get_icon("chevron-down", 14, ON_ACCENT))
        self.arrow.setIconSize(QSize(14, 14))
        self.arrow.setAccessibleName("More save options")
        self.arrow.setToolTip("More save options")
        self.menu = make_menu(self)
        self.menu.setObjectName("SaveMenu")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.main)
        row.addWidget(self.arrow)

        self.main.clicked.connect(lambda _checked=False: self.clicked.emit())
        self.arrow.clicked.connect(lambda _checked=False: self._show_menu())

    def _show_menu(self) -> None:
        size = self.menu.sizeHint()
        self.menu.popup(self.mapToGlobal(QPoint(self.width() - size.width(), self.height() + 6)))


class _HeaderRow(QWidget):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        event.accept()


class CollapsibleSection(QFrame):
    """Inspector section: accent icon, bold title, chevron at the right; click to collapse."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        icon_name: str | None = None,
        expanded: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("InspectorSection")
        self._expanded = expanded

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 4, 16, 14)
        outer.setSpacing(0)

        header = _HeaderRow()
        header.setFixedHeight(40)
        self._header_row = QHBoxLayout(header)
        self._header_row.setContentsMargins(0, 0, 0, 0)
        self._header_row.setSpacing(9)
        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(get_pixmap(icon_name, 16, ACCENT_TEXT))
            self._header_row.addWidget(icon_label)
        self._title_label = QLabel(title)
        self._title_label.setObjectName("SectionTitle")
        self._header_row.addWidget(self._title_label)
        self._header_row.addStretch(1)
        self._chevron = QLabel()
        self._header_row.addWidget(self._chevron)
        header.clicked.connect(self._toggle)
        outer.addWidget(header)

        self._body = QWidget()
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(10)
        outer.addWidget(self._body)

        self._body.setVisible(self._expanded)
        self._update_chevron()

    def add_header_widget(self, widget: QWidget) -> None:
        """Insert a widget (e.g. a count badge) right after the title."""
        self._header_row.insertWidget(self._header_row.indexOf(self._title_label) + 1, widget)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._update_chevron()
        self.toggled.emit(self._expanded)

    def _update_chevron(self) -> None:
        name = "chevron-down" if self._expanded else "chevron-right"
        self._chevron.setPixmap(get_pixmap(name, 15, TEXT_MUTED))
