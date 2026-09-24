from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from brush_watermark.rendering.colors import closest_swatch_color, normalize_text_color


class ColorSwatchPicker(QWidget):
    """Row of colour swatches; the selected one gets an accent ring (QSS ``#Swatch:checked``)."""

    color_changed = Signal(str)

    SWATCH_SIZE = 22

    def __init__(self):
        super().__init__()
        self._row = QHBoxLayout(self)
        self._row.setSpacing(5)
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
            button.setObjectName("Swatch")
            button.setCheckable(True)
            button.setFixedSize(self.SWATCH_SIZE, self.SWATCH_SIZE)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(hex_color)
            button.setAccessibleName(f"Colour {hex_color}")
            # Per-image data colour, not a UI token.
            button.setStyleSheet(f"QPushButton#Swatch {{ background: {hex_color}; }}")
            button.clicked.connect(lambda _checked=False, value=hex_color: self._select(value, emit=True))
            self._row.addWidget(button)
            self._buttons.append(button)
        self._row.addStretch(1)
        self.set_selected(selected or self._selected)

    def selected_color(self) -> str:
        return self._selected

    def set_selected(self, color: str):
        if not self._colors:
            self._selected = normalize_text_color(color)
            return
        self._selected = closest_swatch_color(color, self._colors)
        self._refresh_checks()

    def _select(self, color: str, emit: bool):
        self._selected = normalize_text_color(color)
        self._refresh_checks()
        if emit:
            self.color_changed.emit(self._selected)

    def _refresh_checks(self):
        for button, hex_color in zip(self._buttons, self._colors):
            button.setChecked(hex_color == self._selected)
