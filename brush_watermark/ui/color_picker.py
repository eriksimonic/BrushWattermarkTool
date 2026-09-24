from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget

from brush_watermark.rendering.colors import normalize_text_color
from brush_watermark.ui.design_tokens import TEXT_LABEL
from brush_watermark.ui.icons import get_icon


class ColorSwatchPicker(QWidget):
    """Grid of colour swatches plus a dashed "Pick from image" button.

    The selected swatch gets an accent ring (QSS ``#Swatch:checked``). A colour
    that isn't in the image palette (picked from the image, or saved from an
    earlier image) gets its own "custom" swatch so it is kept exactly.
    """

    color_changed = Signal(str)
    pick_requested = Signal()

    SWATCH_SIZE = 22
    # 11 × 22 px + 10 × 5 px gaps fills the inspector's 298 px body width; the
    # custom swatch and the pick button wrap onto a second row.
    COLUMNS = 11

    def __init__(self):
        super().__init__()
        self._grid = QGridLayout(self)
        self._grid.setHorizontalSpacing(5)
        self._grid.setVerticalSpacing(5)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._buttons: list[QPushButton] = []
        self._colors: list[str] = []
        self._custom: str | None = None
        self._custom_button: QPushButton | None = None
        self._selected = "#ffffff"

        # Built once and re-added on every rebuild (set_swatches deletes the rest).
        self.pick_button = QPushButton()
        self.pick_button.setObjectName("PickSwatch")
        self.pick_button.setCheckable(True)
        self.pick_button.setFixedSize(self.SWATCH_SIZE, self.SWATCH_SIZE)
        self.pick_button.setIcon(get_icon("plus", 12, TEXT_LABEL))
        self.pick_button.setIconSize(QSize(12, 12))
        self.pick_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pick_button.setToolTip("Pick from image (I)")
        self.pick_button.setAccessibleName("Pick from image")
        self.pick_button.clicked.connect(lambda _checked=False: self._on_pick_clicked())

    def _make_swatch(self, hex_color: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("Swatch")
        button.setCheckable(True)
        button.setFixedSize(self.SWATCH_SIZE, self.SWATCH_SIZE)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setToolTip(hex_color)
        button.setAccessibleName(f"Colour {hex_color}")
        # Per-image data colour, not a UI token.
        button.setStyleSheet(f"QPushButton#Swatch {{ background: {hex_color}; }}")
        button.clicked.connect(lambda _checked=False, value=hex_color: self._select(value, emit=True))
        return button

    def _rebuild(self) -> None:
        while self._grid.count():
            widget = self._grid.takeAt(0).widget()
            if widget is not None and widget is not self.pick_button:
                widget.deleteLater()
        self._buttons = [self._make_swatch(color) for color in self._colors]
        self._custom_button = self._make_swatch(self._custom) if self._custom else None
        widgets = list(self._buttons)
        if self._custom_button is not None:
            widgets.append(self._custom_button)
        widgets.append(self.pick_button)
        for index, widget in enumerate(widgets):
            self._grid.addWidget(widget, index // self.COLUMNS, index % self.COLUMNS)
        self._refresh_checks()

    def set_swatches(self, colors: list[str], selected: str | None = None):
        self._colors = [normalize_text_color(color) for color in colors]
        self._custom = None
        self._selected = normalize_text_color(selected or self._selected)
        if self._selected not in self._colors:
            self._custom = self._selected
        self._rebuild()

    def selected_color(self) -> str:
        return self._selected

    def custom_color(self) -> str | None:
        return self._custom

    def set_selected(self, color: str):
        """Select `color`; one outside the palette becomes the custom swatch."""
        self._selected = normalize_text_color(color)
        if self._selected not in self._colors and self._selected != self._custom:
            self._custom = self._selected
            self._rebuild()
        else:
            self._refresh_checks()

    def select_picked(self, color: str) -> None:
        """A colour sampled from the image: select it and tell listeners."""
        self.set_selected(color)
        self.color_changed.emit(self._selected)

    def set_picking(self, picking: bool) -> None:
        self.pick_button.setChecked(picking)

    def _on_pick_clicked(self) -> None:
        # The window decides whether pick mode is on and reports it back.
        self.pick_button.setChecked(False)
        self.pick_requested.emit()

    def _select(self, color: str, emit: bool):
        self._selected = normalize_text_color(color)
        self._refresh_checks()
        if emit:
            self.color_changed.emit(self._selected)

    def _refresh_checks(self):
        for button, hex_color in zip(self._buttons, self._colors):
            button.setChecked(hex_color == self._selected)
        if self._custom_button is not None:
            self._custom_button.setChecked(self._custom == self._selected)
