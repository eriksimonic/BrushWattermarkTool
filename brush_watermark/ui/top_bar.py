"""Top bar: logo and menus, active file info, Original/Watermarked toggle, save actions."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QWidget

from brush_watermark.ui.controls import SegmentedControl, SplitButton, make_menu
from brush_watermark.ui.design_tokens import ON_ACCENT, TEXT, TEXT_MUTED, TEXT_SECONDARY
from brush_watermark.ui.icons import get_icon, get_pixmap


def _vertical_divider(object_name: str, height: int) -> QFrame:
    divider = QFrame()
    divider.setObjectName(object_name)
    divider.setFixedSize(1, height)
    return divider


class TopBar(QFrame):
    preview_changed = Signal(bool)
    save_and_close = Signal()
    save_copy_and_close = Signal()
    save_all_and_close = Signal()
    exit_without_saving = Signal()

    HEIGHT = 52

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(self.HEIGHT)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 12, 0)
        row.setSpacing(12)

        logo = QLabel()
        logo.setObjectName("LogoMark")
        logo.setFixedSize(30, 30)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(get_pixmap("paintbrush", 17, ON_ACCENT))
        self._menu_row = QHBoxLayout()
        self._menu_row.setSpacing(2)
        left = QHBoxLayout()
        left.setSpacing(10)
        left.addWidget(logo)
        left.addLayout(self._menu_row)
        row.addLayout(left)
        row.addWidget(_vertical_divider("TopDivider", 22))

        file_icon = QLabel()
        file_icon.setPixmap(get_pixmap("image", 15, TEXT_MUTED))
        self.file_name_label = QLabel()
        self.file_name_label.setObjectName("FileName")
        self.serial_chip = QLabel()
        self.serial_chip.setObjectName("SerialChip")
        self.serial_chip.setToolTip("Image serial")
        self.serial_chip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.index_badge = QLabel()
        self.index_badge.setObjectName("CountBadge")
        self.index_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.unsaved_indicator = QWidget()
        unsaved_row = QHBoxLayout(self.unsaved_indicator)
        unsaved_row.setContentsMargins(0, 0, 0, 0)
        unsaved_row.setSpacing(5)
        dot = QLabel()
        dot.setObjectName("UnsavedDot")
        dot.setFixedSize(6, 6)
        unsaved_label = QLabel("Unsaved")
        unsaved_label.setObjectName("UnsavedLabel")
        unsaved_row.addWidget(dot)
        unsaved_row.addWidget(unsaved_label)
        self.unsaved_indicator.hide()
        info = QHBoxLayout()
        info.setSpacing(8)
        for widget in (file_icon, self.file_name_label, self.serial_chip, self.index_badge, self.unsaved_indicator):
            info.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addLayout(info)

        row.addStretch(1)
        self.preview_toggle = SegmentedControl(["Original", "Watermarked"])
        self.preview_toggle.setCurrentIndex(1)
        self.preview_toggle.setAccessibleName("Preview")
        row.addWidget(self.preview_toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)

        self.exit_button = QPushButton("Exit")
        self.exit_button.setObjectName("GhostButton")
        self.exit_button.setIcon(get_icon("x", 15, TEXT_SECONDARY))
        self.exit_button.setToolTip("Exit without saving")
        self.save_copy_button = QPushButton("Save copy")
        self.save_copy_button.setObjectName("SecondaryButton")
        self.save_copy_button.setIcon(get_icon("copy", 15, TEXT))
        self.save_copy_button.setToolTip("Save a watermarked copy next to the original and close")
        self.save_split = SplitButton("Save && close", "save")
        menu = self.save_split.menu
        self.save_close_action = menu.addAction(get_icon("save", 15, TEXT), "Save && close")
        self.save_all_action = menu.addAction(get_icon("images", 15, TEXT), "Save all && close")
        menu.addSeparator()
        self.save_copy_action = menu.addAction(get_icon("copy", 15, TEXT), "Save copy && close")
        for button in (self.exit_button, self.save_copy_button):
            button.setIconSize(QSize(15, 15))
        right = QHBoxLayout()
        right.setSpacing(8)
        right.addWidget(self.exit_button)
        right.addWidget(self.save_copy_button)
        right.addWidget(self.save_split)
        row.addLayout(right)

        self.preview_toggle.currentChanged.connect(lambda index: self.preview_changed.emit(index == 0))
        self.exit_button.clicked.connect(lambda _checked=False: self.exit_without_saving.emit())
        self.save_copy_button.clicked.connect(lambda _checked=False: self.save_copy_and_close.emit())
        self.save_split.clicked.connect(self.save_and_close.emit)
        self.save_close_action.triggered.connect(lambda _checked=False: self.save_and_close.emit())
        self.save_all_action.triggered.connect(lambda _checked=False: self.save_all_and_close.emit())
        self.save_copy_action.triggered.connect(lambda _checked=False: self.save_copy_and_close.emit())
        self.set_multi_document_mode(False)

    def add_menu(self, title: str) -> QMenu:
        button = QPushButton(title)
        button.setObjectName("MenuButton")
        menu = make_menu(button)
        button.setMenu(menu)
        self._menu_row.addWidget(button)
        return menu

    def show_original(self) -> bool:
        return self.preview_toggle.currentIndex() == 0

    def set_file_info(self, name: str, serial: str | None, index: int, count: int) -> None:
        self.file_name_label.setText(name)
        self.serial_chip.setText(f"#{serial}" if serial else "")
        self.serial_chip.setVisible(bool(serial))
        self.index_badge.setText(f"{index + 1} / {count}")
        self.index_badge.setVisible(count > 1)

    def set_unsaved(self, dirty: bool) -> None:
        self.unsaved_indicator.setVisible(dirty)

    def set_multi_document_mode(self, enabled: bool, edited_count: int = 0) -> None:
        self.save_all_action.setVisible(enabled)
        self.save_all_action.setText(
            f"Save all && close ({edited_count} edited)" if edited_count else "Save all && close"
        )
