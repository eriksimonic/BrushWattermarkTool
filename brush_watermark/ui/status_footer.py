"""Bottom status bar: key hints, the edit-target note, version and update status."""

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.controls import ElidedLabel, KeyHint
from brush_watermark.ui.design_tokens import ON_ACCENT, SUCCESS, TEXT_MUTED, WARNING
from brush_watermark.ui.icons import get_icon

FOOTER_HINTS = (
    ("Wheel", "Strength"),
    ("Alt+Wheel", "Brush size"),
    ("Dbl-click", "Add anchor"),
    ("Del", "Remove anchor"),
)


class StatusFooter(QFrame):
    update_now = Signal()

    HEIGHT = 30

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatusFooter")
        self.setFixedHeight(self.HEIGHT)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(18)
        for keys, text in FOOTER_HINTS:
            row.addWidget(KeyHint(keys, text, text_object_name="FooterText"))
        row.addStretch(1)
        note = ElidedLabel("Controls edit the selected layer, or tool defaults when nothing is selected")
        note.setObjectName("FooterText")
        row.addWidget(note)
        divider = QFrame()
        divider.setObjectName("FooterDivider")
        divider.setFixedSize(1, 12)
        row.addWidget(divider)

        status = QHBoxLayout()
        status.setSpacing(6)
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(6, 6)
        self.version_label = QLabel()
        self.version_label.setObjectName("FooterText")
        self.update_link = QLabel()
        self.update_link.setObjectName("FooterText")
        self.update_link.setOpenExternalLinks(True)
        self.update_link.hide()
        self.update_now_button = QPushButton()
        self.update_now_button.setObjectName("FooterUpdateButton")
        self.update_now_button.setIcon(get_icon("download", 11, ON_ACCENT))
        self.update_now_button.setIconSize(QSize(11, 11))
        self.update_now_button.hide()
        self.progress_label = QLabel()
        self.progress_label.setObjectName("FooterText")
        self.progress_label.hide()
        for widget in (self._status_dot, self.version_label, self.update_link, self.update_now_button, self.progress_label):
            status.addWidget(widget)
        row.addLayout(status)

        self.update_now_button.clicked.connect(lambda _checked=False: self.update_now.emit())
        self._set_dot(TEXT_MUTED)

    def _set_dot(self, color: str) -> None:
        self._status_dot.setStyleSheet(f"background: {color}; border-radius: 3px;")

    def set_version_info(self, current_version: str, result: UpdateCheckResult | None = None) -> None:
        self.update_now_button.hide()
        self.update_link.hide()
        if result is None:
            self.version_label.setText(f"v{current_version} · Checking for updates…")
            self._set_dot(TEXT_MUTED)
            return
        if result.check_failed:
            self.version_label.setText(f"v{current_version}")
            self._set_dot(TEXT_MUTED)
            return
        if result.update_available and result.latest_version:
            self.version_label.setText(f"v{current_version}")
            self._set_dot(WARNING)
            if result.download_url:
                self.update_now_button.setText(f"Update to v{result.latest_version}")
                self.update_now_button.show()
            else:
                self.update_link.setText(
                    f'<a href="{result.release_url}">v{result.latest_version} available — open release page</a>'
                )
                self.update_link.show()
            return
        self.version_label.setText(f"v{current_version} · Up to date")
        self._set_dot(SUCCESS)

    def set_update_progress(self, percent: int, message: str) -> None:
        self.update_now_button.setEnabled(False)
        self.progress_label.setText(message if percent >= 100 else f"{message} ({percent}%)")
        self.progress_label.show()

    def clear_update_progress(self) -> None:
        self.update_now_button.setEnabled(True)
        self.progress_label.hide()
        self.progress_label.setText("")
