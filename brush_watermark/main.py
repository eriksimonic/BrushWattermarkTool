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


def select_jpg_file() -> Optional[Path]:
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Select JPG image",
        last_image_dir(),
        "JPEG images (*.jpg *.jpeg);;All files (*.*)",
    )
    if not file_path:
        return None
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        QMessageBox.critical(None, APP_NAME, "Only JPG and JPEG files are supported.")
        return None
    save_settings({"last_image_dir": str(path.parent)})
    return path


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


def resolve_image_path() -> Optional[Path]:
    if len(sys.argv) >= 2:
        return Path(sys.argv[1])
    return select_jpg_file()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(load_app_icon())

    image_path = resolve_image_path()
    if image_path is None:
        return 0
    try:
        from brush_watermark.ui.main_window import MainWindow

        settings = Settings.from_dict(load_settings())
        window = MainWindow(image_path, settings)
        window.show()
        return app.exec()
    except (FileNotFoundError, ValueError, OSError) as exc:
        QMessageBox.critical(None, APP_NAME, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
