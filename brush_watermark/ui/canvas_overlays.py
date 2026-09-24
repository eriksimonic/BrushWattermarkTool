"""Floating panels over the canvas: tool hints, zoom, brush readout."""

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QWidget,
)

from brush_watermark.models import ToolMode
from brush_watermark.ui.controls import KeyHint
from brush_watermark.ui.design_tokens import SHADOW, TEXT, TEXT_SECONDARY, rgba
from brush_watermark.ui.icons import get_icon
from brush_watermark.ui.zoom import parse_zoom_percent

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
    ToolMode.PAN: ("Pan", (("Drag", "Pan"), ("Space", "Hold to pan in any tool"))),
    ToolMode.ZOOM: ("Zoom", (("Click", "Zoom in"), ("Alt+Click", "Zoom out"))),
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


class ZoomField(QLineEdit):
    """The zoom % as an editable field: Enter applies, Esc reverts; both hand focus back."""

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.setText(self.property("shownText") or "")
            self.clearFocus()
            return
        super().keyPressEvent(event)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clearFocus()


class ZoomPill(FloatingPanel):
    zoom_mode_changed = Signal(bool)  # True = 1:1, False = Fit
    zoom_step_requested = Signal(int)  # +1 zoom in, -1 zoom out
    zoom_percent_entered = Signal(float)  # a scale typed into the % field

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.row.setContentsMargins(4, 3, 4, 3)
        self.row.setSpacing(2)
        self.zoom_out_btn = self._icon_button("minus", "Zoom out")
        self.zoom_in_btn = self._icon_button("plus", "Zoom in")
        self.percent_edit = ZoomField("100%")
        self.percent_edit.setObjectName("ZoomPercent")
        self.percent_edit.setFixedWidth(50)
        self.percent_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percent_edit.setToolTip("Zoom — type a percentage and press Enter")
        self.percent_edit.setAccessibleName("Zoom percentage")
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setObjectName("PillButton")
        self.fit_btn.setIcon(get_icon("maximize", 14, TEXT_SECONDARY))
        self.fit_btn.setIconSize(QSize(14, 14))
        self.fit_btn.setToolTip("Fit the image to the window")
        self.one_to_one_btn = QPushButton("1:1")
        self.one_to_one_btn.setObjectName("PillButtonMono")
        self.one_to_one_btn.setToolTip("Actual size (100%)")
        # Checked state is set from outside (set_zoom_state): at e.g. 150 %
        # neither is checked, which an exclusive QButtonGroup can't show.
        for button in (self.fit_btn, self.one_to_one_btn):
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.fit_btn.setChecked(True)
        self.row.addWidget(self.zoom_out_btn)
        self.row.addWidget(self.percent_edit)
        self.row.addWidget(self.zoom_in_btn)
        self.row.addWidget(_pill_divider())
        self.row.addWidget(self.fit_btn)
        self.row.addWidget(self.one_to_one_btn)
        self.fit_btn.clicked.connect(lambda _checked=False: self._on_mode_clicked(False))
        self.one_to_one_btn.clicked.connect(lambda _checked=False: self._on_mode_clicked(True))
        self.zoom_out_btn.clicked.connect(lambda _checked=False: self.zoom_step_requested.emit(-1))
        self.zoom_in_btn.clicked.connect(lambda _checked=False: self.zoom_step_requested.emit(1))
        self.percent_edit.editingFinished.connect(self._on_percent_entered)

    @staticmethod
    def _icon_button(icon_name: str, tip: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("PillIconButton")
        button.setFixedSize(28, 28)
        button.setIcon(get_icon(icon_name, 15, TEXT_SECONDARY))
        button.setIconSize(QSize(15, 15))
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def _on_mode_clicked(self, one_to_one: bool) -> None:
        # Undo the click's own toggle; the window reports the real state back.
        self.fit_btn.setChecked(not one_to_one)
        self.one_to_one_btn.setChecked(one_to_one)
        self.zoom_mode_changed.emit(one_to_one)

    def _on_percent_entered(self) -> None:
        scale = parse_zoom_percent(self.percent_edit.text())
        if scale is None:
            self.percent_edit.setText(self.percent_edit.property("shownText") or "")
            return
        self.zoom_percent_entered.emit(scale)

    def set_zoom_percent(self, percent: int) -> None:
        text = f"{percent}%"
        self.percent_edit.setProperty("shownText", text)
        if not self.percent_edit.hasFocus():
            self.percent_edit.setText(text)

    def set_zoom_state(self, percent: int, fit: bool) -> None:
        self.set_zoom_percent(percent)
        self.fit_btn.setChecked(fit)
        self.one_to_one_btn.setChecked(not fit and percent == 100)


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
