import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from brush_watermark.config import (
    APP_NAME,
    SUPPORTED_EXTENSIONS,
    app_icon_path,
    last_image_dir,
    load_settings,
    save_settings,
)
from brush_watermark.models import Settings


def select_jpg_files() -> list[Path]:
    file_paths, _ = QFileDialog.getOpenFileNames(
        None,
        "Select JPG image(s)",
        last_image_dir(),
        "JPEG images (*.jpg *.jpeg);;All files (*.*)",
    )
    if not file_paths:
        return []
    paths = [Path(file_path) for file_path in file_paths]
    invalid = [path for path in paths if path.suffix.lower() not in SUPPORTED_EXTENSIONS]
    if invalid:
        QMessageBox.critical(None, APP_NAME, "Only JPG and JPEG files are supported.")
        return []
    save_settings({"last_image_dir": str(paths[0].parent)})
    return paths


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

    image_paths = resolve_image_paths()
    if not image_paths:
        return 0
    try:
        from brush_watermark.ui.main_window import MainWindow

        settings = Settings.from_dict(load_settings())
        window = MainWindow(image_paths, settings)
        window.show()
        return app.exec()
    except (FileNotFoundError, ValueError, OSError) as exc:
        QMessageBox.critical(None, APP_NAME, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
