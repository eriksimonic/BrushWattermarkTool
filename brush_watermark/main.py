import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox

from brush_watermark.config import (
    APP_NAME,
    SUPPORTED_EXTENSIONS,
    app_icon_path,
    load_settings,
)
from brush_watermark.models import Settings
from brush_watermark.ui.app_fonts import register_app_fonts, ui_font
from brush_watermark.ui.file_dialogs import select_jpg_files


def load_app_icon() -> QIcon:
    icon_path = app_icon_path()
    if not icon_path.is_file():
        return QIcon()
    source = QPixmap(str(icon_path))
    side = max(source.width(), source.height())
    square = QPixmap(side, side)
    square.fill(Qt.GlobalColor.transparent)
    painter = QPainter(square)
    painter.drawPixmap((side - source.width()) // 2, (side - source.height()) // 2, source)
    painter.end()
    return QIcon(square)


def resolve_image_paths() -> list[Path]:
    """Resolve the image(s) to open.

    Lightroom's "Edit In" external editor passes every selected photo as a
    separate command-line argument, so all of argv[1:] are collected here
    (filtered to supported extensions) rather than just argv[1].
    """
    if len(sys.argv) >= 2:
        return [
            Path(arg) for arg in sys.argv[1:] if Path(arg).suffix.lower() in SUPPORTED_EXTENSIONS
        ]
    return select_jpg_files()


def main() -> int:

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(load_app_icon())
    register_app_fonts()
    app.setFont(ui_font())

    image_paths = resolve_image_paths()
    if not image_paths:
        return 0

    collector = None
    if len(sys.argv) >= 2:
        # CLI-arg launches are how Explorer's context menu opens images. Explorer
        # invokes the app once per selected file rather than once with every
        # path (MultiSelectModel=Player doesn't help here — see launch_collector),
        # so merge sibling launches into one window instead of opening several.
        from brush_watermark.ui.launch_collector import claim_primary_or_forward

        forwarded, collector = claim_primary_or_forward(image_paths)
        if forwarded:
            return 0

    from brush_watermark.services.document import format_load_errors, load_documents
    from brush_watermark.ui.main_window import MainWindow

    settings = Settings.from_dict(load_settings())
    docs, errors = load_documents(image_paths, settings)
    # Siblings have already exited after handing us their paths, so if none of
    # our own images load, open theirs rather than dropping them.
    while not docs and collector is not None:
        forwarded_paths = collector.wait_for_paths()
        if not forwarded_paths:
            break
        docs, more_errors = load_documents(forwarded_paths, settings)
        errors += more_errors

    if not docs:
        QMessageBox.critical(None, APP_NAME, format_load_errors(errors))
        return 1
    window = MainWindow(docs)
    if collector is not None:
        collector.set_receiver(window.add_documents)
    window.show()
    if errors:
        QMessageBox.warning(window, APP_NAME, format_load_errors(errors))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
