"""Floating panels over the canvas: tool hints, zoom, brush readout."""

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
)

from brush_watermark.models import ToolMode
from brush_watermark.ui.controls import KeyHint
from brush_watermark.ui.design_tokens import SHADOW, TEXT, TEXT_SECONDARY, rgba
from brush_watermark.ui.icons import get_icon

# Per-tool hints, matching what MainWindow/CanvasWidget actually handle.
TOOL_HINTS: dict[ToolMode, tuple[str, tuple[tuple[str, str], ...]]] = {
    ToolMode.POINTER: ("Select", (("Click", "Select / deselect"),)),
    ToolMode.BRUSH: (
        "Brush",
        (
            ("Drag", "Freehand"),
            ("Click", "Straight line"),
            ("Click end", "Resume"),
            ("Right-click", "Stop"),
            ("Esc", "Cancel line"),
        ),
    ),
    ToolMode.PATH: ("Path", (("Drag", "Move anchor"), ("Dbl-click", "Add anchor"), ("Del", "Remove anchor"))),
    ToolMode.ERASER: ("Eraser", (("Drag", "Erase"), ("Alt+Wheel", "Size"))),
}


def tool_hint(tool: ToolMode) -> tuple[str, tuple[tuple[str, str], ...]]:
    return TOOL_HINTS[tool]


def _pill_divider() -> QFrame:
    divider = QFrame()
    divider.setObjectName("PillDivider")
    divider.setFixedSize(1, 16)
    return divider


class FloatingPanel(QFrame):
    """Rounded translucent panel with a soft drop shadow."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FloatingPanel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        color = QColor(SHADOW)
        color.setAlphaF(0.35)
        shadow.setColor(color)
        self.setGraphicsEffect(shadow)
        self.row = QHBoxLayout(self)


class HintPill(FloatingPanel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(36)
        self.row.setContentsMargins(14, 0, 14, 0)
        self.row.setSpacing(10)
        self.tool_label = QLabel()
        self.tool_label.setObjectName("HintTool")
        self.row.addWidget(self.tool_label)
        self.row.addWidget(_pill_divider())
        self._hints: list[QWidget] = []

    def set_tool(self, tool: ToolMode) -> None:
        name, hints = tool_hint(tool)
        self.tool_label.setText(name)
        for widget in self._hints:
            widget.setParent(None)
            widget.deleteLater()
        self._hints = [KeyHint(keys, text) for keys, text in hints]
        for widget in self._hints:
            self.row.addWidget(widget)
            widget.show()
        self.adjustSize()


class ZoomPill(FloatingPanel):
    zoom_mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.row.setContentsMargins(4, 3, 4, 3)
        self.row.setSpacing(2)
        self.percent_label = QLabel("100%")
        self.percent_label.setObjectName("ZoomPercent")
        self.percent_label.setFixedWidth(46)
        self.percent_label.setToolTip("Current preview zoom")
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setObjectName("PillButton")
        self.fit_btn.setIcon(get_icon("maximize", 14, TEXT_SECONDARY))
        self.fit_btn.setIconSize(QSize(14, 14))
        self.fit_btn.setToolTip("Fit the image to the window")
        self.one_to_one_btn = QPushButton("1:1")
        self.one_to_one_btn.setObjectName("PillButtonMono")
        self.one_to_one_btn.setToolTip("Actual size (100%)")
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for button in (self.fit_btn, self.one_to_one_btn):
            button.setCheckable(True)
            self._group.addButton(button)
        self.fit_btn.setChecked(True)
        self.row.addWidget(self.percent_label)
        self.row.addWidget(_pill_divider())
        self.row.addWidget(self.fit_btn)
        self.row.addWidget(self.one_to_one_btn)
        self._group.buttonToggled.connect(self._on_toggled)

    def _on_toggled(self, button: QPushButton, checked: bool) -> None:
        if checked:
            self.zoom_mode_changed.emit(button is self.one_to_one_btn)

    def set_zoom_percent(self, percent: int) -> None:
        self.percent_label.setText(f"{percent}%")


class BrushReadout(FloatingPanel):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(38)
        self.row.setContentsMargins(14, 0, 14, 0)
        self.row.setSpacing(12)
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(14, 14)
        self.size_label = QLabel()
        self.strength_label = QLabel()
        for label in (self.size_label, self.strength_label):
            label.setObjectName("ReadoutText")
        self.blend_label = QLabel()
        self.blend_label.setObjectName("HintText")
        self.row.addWidget(self.color_dot)
        self.row.addWidget(self.size_label)
        self.row.addWidget(self._slash())
        self.row.addWidget(self.strength_label)
        self.row.addWidget(self._slash())
        self.row.addWidget(self.blend_label)

    @staticmethod
    def _slash() -> QLabel:
        label = QLabel("/")
        label.setObjectName("ReadoutSlash")
        return label

    def set_values(self, color: str, size_px: int, strength_text: str, blend_label: str) -> None:
        # `color` is the stroke's data colour, not a UI token.
        self.color_dot.setStyleSheet(
            f"background: {color}; border: 1px solid {rgba(TEXT, 0.25)}; border-radius: 7px;"
        )
        self.size_label.setText(f"{size_px} px")
        self.strength_label.setText(strength_text)
        self.blend_label.setText(blend_label)
        self.adjustSize()


class CanvasArea(QWidget):
    """Holds the canvas scroll area and floats the overlay panels above it."""

    MARGIN = 16

    def __init__(self, scroll_area: QScrollArea, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.scroll_area = scroll_area
        scroll_area.setParent(self)
        self.hint_pill = HintPill(self)
        self.zoom_pill = ZoomPill(self)
        self.brush_readout = BrushReadout(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scroll_area.setGeometry(self.rect())
        self.refresh_overlays()

    def refresh_overlays(self) -> None:
        m = self.MARGIN
        for panel in (self.hint_pill, self.zoom_pill, self.brush_readout):
            panel.adjustSize()
            panel.raise_()
        self.hint_pill.move((self.width() - self.hint_pill.width()) // 2, m)
        self.zoom_pill.move(m, self.height() - self.zoom_pill.height() - m)
        self.brush_readout.move(
            self.width() - self.brush_readout.width() - m,
            self.height() - self.brush_readout.height() - m,
        )
