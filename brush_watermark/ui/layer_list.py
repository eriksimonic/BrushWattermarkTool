"""Inspector layer rows: eye toggle, type icon, name and a one-line summary."""

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from brush_watermark.ui.design_tokens import ICON_DISABLED, TEXT_LABEL, TEXT_SECONDARY
from brush_watermark.ui.icons import get_icon, get_pixmap


@dataclass(frozen=True)
class LayerItem:
    name: str
    meta: str
    visible: bool


class _LayerRow(QFrame):
    clicked = Signal()
    eye_clicked = Signal()

    def __init__(self, item: LayerItem, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("LayerRow")
        self.setProperty("selected", False)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.eye = QPushButton()
        self.eye.setObjectName("LayerEye")
        self.eye.setFixedSize(28, 28)
        self.eye.setIconSize(QSize(15, 15))
        if item.visible:
            self.eye.setIcon(get_icon("eye", 15, TEXT_SECONDARY))
            tip = "Hide layer"
        else:
            self.eye.setIcon(get_icon("eye-off", 15, ICON_DISABLED))
            tip = "Show layer"
        self.eye.setToolTip(tip)
        self.eye.setAccessibleName(tip)

        tile = QLabel()
        tile.setObjectName("LayerIcon")
        tile.setFixedSize(30, 30)
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.setPixmap(get_pixmap("paintbrush", 15, TEXT_LABEL))

        self.name_label = QLabel(item.name)
        self.name_label.setObjectName("LayerName")
        self.meta_label = QLabel(item.meta)
        self.meta_label.setObjectName("LayerMeta")
        for label in (self.name_label, self.meta_label):
            label.setProperty("layerHidden", not item.visible)
        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(2)
        texts.addWidget(self.name_label)
        texts.addWidget(self.meta_label)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 0, 8, 0)
        row.setSpacing(6)
        row.addWidget(self.eye)
        row.addSpacing(4)
        row.addWidget(tile)
        row.addSpacing(4)
        row.addLayout(texts, 1)

        self.eye.clicked.connect(lambda _checked=False: self.eye_clicked.emit())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        if self.property("selected") == selected:
            return
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class LayerList(QWidget):
    layer_clicked = Signal(int)
    visibility_toggled = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._empty = QLabel("No layers yet — draw a stroke on the photo.")
        self._empty.setObjectName("HintLabel")
        self._layout.addWidget(self._empty)
        self._rows: list[_LayerRow] = []

    def rows(self) -> list[_LayerRow]:
        return list(self._rows)

    def set_layers(self, items: list[LayerItem], selected: int = -1) -> None:
        for row in self._rows:
            row.setParent(None)
            row.deleteLater()
        self._rows = []
        for index, item in enumerate(items):
            row = _LayerRow(item)
            row.clicked.connect(lambda i=index: self.layer_clicked.emit(i))
            row.eye_clicked.connect(lambda i=index: self.visibility_toggled.emit(i))
            self._layout.addWidget(row)
            self._rows.append(row)
        self._empty.setVisible(not items)
        self.set_selected(selected)

    def set_selected(self, index: int) -> None:
        for i, row in enumerate(self._rows):
            row.set_selected(i == index)
