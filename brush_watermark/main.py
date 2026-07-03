import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from brush_watermark.config import APP_NAME, SUPPORTED_EXTENSIONS, load_settings
from brush_watermark.models import Settings
from brush_watermark.ui.main_window import MainWindow


def select_jpg_file() -> Optional[Path]:
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Select JPG image",
        "",
        "JPEG images (*.jpg *.jpeg);;All files (*.*)",
    )
    if not file_path:
        return None
    path = Path(file_path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        QMessageBox.critical(None, APP_NAME, "Only JPG and JPEG files are supported.")
        return None
    return path


def resolve_image_path() -> Optional[Path]:
    if len(sys.argv) >= 2:
        return Path(sys.argv[1])
    return select_jpg_file()


def main() -> int:
    app = QApplication(sys.argv)
    image_path = resolve_image_path()
    if image_path is None:
        return 0
    try:
        settings = Settings.from_dict(load_settings())
        window = MainWindow(image_path, settings)
        window.show()
        return app.exec()
    except (FileNotFoundError, ValueError, OSError) as exc:
        QMessageBox.critical(None, APP_NAME, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
