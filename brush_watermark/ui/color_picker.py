from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from brush_watermark.rendering.colors import closest_swatch_color, normalize_text_color, parse_rgb
from brush_watermark.ui.design_tokens import BORDER, SELECTION_BORDER


class ColorSwatchPicker(QWidget):
    color_changed = Signal(str)

    SWATCH_SIZE = 20

    def __init__(self):
        super().__init__()
        self._row = QHBoxLayout(self)
        self._row.setSpacing(3)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._buttons: list[QPushButton] = []
        self._colors: list[str] = []
        self._selected = "#ffffff"

    def set_swatches(self, colors: list[str], selected: str | None = None):
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons = []
        self._colors = [normalize_text_color(color) for color in colors]
        for hex_color in self._colors:
            button = QPushButton()
            button.setFixedSize(self.SWATCH_SIZE, self.SWATCH_SIZE)
            button.setToolTip(hex_color)
            button.clicked.connect(lambda _checked=False, value=hex_color: self._select(value, emit=True))
            self._row.addWidget(button)
            self._buttons.append(button)
        self._row.addStretch(1)
        self.set_selected(selected or self._selected)

    def swatch_colors(self) -> list[str]:
        return list(self._colors)

    def selected_color(self) -> str:
        return self._selected

    def set_selected(self, color: str):
        if not self._colors:
            self._selected = normalize_text_color(color)
            return
        self._selected = closest_swatch_color(color, self._colors)
        self._refresh_styles()

    def _select(self, color: str, emit: bool):
        self._selected = normalize_text_color(color)
        self._refresh_styles()
        if emit:
            self.color_changed.emit(self._selected)

    def _refresh_styles(self):
        for button, hex_color in zip(self._buttons, self._colors):
            r, g, b = parse_rgb(hex_color)
            border = f"2px solid {SELECTION_BORDER}" if hex_color == self._selected else f"2px solid {BORDER}"
            button.setStyleSheet(
                f"QPushButton {{ background-color: rgb({r}, {g}, {b}); border: {border}; "
                f"border-radius: 4px; min-width: {self.SWATCH_SIZE}px; max-width: {self.SWATCH_SIZE}px; "
                f"min-height: {self.SWATCH_SIZE}px; max-height: {self.SWATCH_SIZE}px; padding: 0; }}"
            )
