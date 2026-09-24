"""Left tool rail: drawing tools with key letters, auto-place, shortcuts popup."""

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QButtonGroup, QFrame, QGridLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from brush_watermark.models import ToolMode
from brush_watermark.ui.app_fonts import mono_font
from brush_watermark.ui.controls import KeyCombo
from brush_watermark.ui.design_tokens import ACCENT_TEXT, TEXT_LABEL, TEXT_MUTED
from brush_watermark.ui.icons import get_icon_checkable

RAIL_TOOLS = (
    (ToolMode.POINTER, "mouse-pointer-2", "Select", "V"),
    (ToolMode.BRUSH, "paintbrush", "Brush", "B"),
    (ToolMode.PATH, "pen-tool", "Path", "A"),
    (ToolMode.ERASER, "eraser", "Eraser", "E"),
)
NAV_TOOLS = (
    (ToolMode.PAN, "hand", "Pan", "H"),
    (ToolMode.ZOOM, "zoom-in", "Zoom", "Z"),
)

# Only shortcuts the app actually handles (MainWindow.keyPressEvent / canvas input).
SHORTCUTS = (
    ("V", "Select tool"),
    ("B", "Brush tool"),
    ("A", "Path tool"),
    ("E", "Eraser tool"),
    ("H", "Pan tool"),
    ("Z", "Zoom tool"),
    ("Space", "Hold to pan"),
    ("Alt+Click", "Zoom out (Zoom)"),
    ("Wheel", "Strength"),
    ("Alt+Wheel", "Brush size"),
    ("Right-click", "Stop drawing (Brush)"),
    ("Dbl-click", "Add anchor (Path)"),
    ("Del", "Remove anchor (Path) / selected layer"),
    ("Esc", "Cancel line / deselect anchor"),
    ("Ctrl+←/→", "Previous / next image"),
    ("Ctrl+S", "Save & close"),
)


class RailButton(QToolButton):
    """40×40 rail button; draws its shortcut letter in the bottom-right corner."""

    SIZE = 40

    def __init__(self, icon_name: str, label: str, key: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("RailButton")
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setIcon(get_icon_checkable(icon_name, 19, TEXT_LABEL, ACCENT_TEXT))
        self.setIconSize(QSize(19, 19))
        self.setToolTip(f"{label} ({key})" if key else label)
        self.setAccessibleName(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._key = key

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._key:
            return
        painter = QPainter(self)
        painter.setFont(mono_font(9))
        painter.setPen(QColor(ACCENT_TEXT if self.isChecked() else TEXT_MUTED))
        painter.drawText(
            self.rect().adjusted(0, 0, -4, -2),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            self._key,
        )
        painter.end()


class ShortcutsPopup(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("PopupPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        grid = QGridLayout(self)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        for row, (keys, text) in enumerate(SHORTCUTS):
            grid.addWidget(KeyCombo(keys), row, 0, Qt.AlignmentFlag.AlignLeft)
            label = QLabel(text)
            label.setObjectName("HintText")
            grid.addWidget(label, row, 1)


class ToolRail(QFrame):
    tool_changed = Signal(object)
    auto_place_requested = Signal()

    WIDTH = 60

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ToolRail")
        self.setFixedWidth(self.WIDTH)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 10, 0, 10)
        column.setSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons: dict[ToolMode, RailButton] = {}
        for tools in (RAIL_TOOLS, NAV_TOOLS):
            for tool, icon_name, label, key in tools:
                button = RailButton(icon_name, label, key)
                button.setCheckable(True)
                button.clicked.connect(lambda _checked=False, t=tool: self.tool_changed.emit(t))
                self._group.addButton(button)
                self.buttons[tool] = button
                column.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(self._divider(), 0, Qt.AlignmentFlag.AlignHCenter)
        self.auto_place_btn = RailButton("wand-2", "Auto-place watermarks")
        self.auto_place_btn.clicked.connect(lambda _checked=False: self.auto_place_requested.emit())
        column.addWidget(self.auto_place_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addStretch(1)
        self.shortcuts_btn = RailButton("keyboard", "Keyboard shortcuts")
        self.shortcuts_btn.clicked.connect(lambda _checked=False: self._show_shortcuts())
        column.addWidget(self.shortcuts_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self.set_active_tool(ToolMode.BRUSH)

    @staticmethod
    def _divider() -> QFrame:
        divider = QFrame()
        divider.setObjectName("RailDivider")
        divider.setFixedSize(24, 1)
        return divider

    def set_active_tool(self, tool: ToolMode) -> None:
        for mode, button in self.buttons.items():
            button.blockSignals(True)
            button.setChecked(mode == tool)
            button.blockSignals(False)

    def _show_shortcuts(self) -> None:
        popup = ShortcutsPopup(self)
        popup.adjustSize()
        anchor = self.shortcuts_btn.mapToGlobal(QPoint(self.shortcuts_btn.width() + 8, self.shortcuts_btn.height()))
        popup.move(anchor.x(), anchor.y() - popup.height())
        popup.show()
