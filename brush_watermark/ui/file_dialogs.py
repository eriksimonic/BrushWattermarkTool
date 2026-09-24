"""File pickers shared by the launcher (main.py) and the window's "Add images"."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from brush_watermark.config import APP_NAME, SUPPORTED_EXTENSIONS, last_image_dir, save_settings


def select_jpg_files(parent: QWidget | None = None) -> list[Path]:
    file_paths, _ = QFileDialog.getOpenFileNames(
        parent,
        "Select JPG image(s)",
        last_image_dir(),
        "JPEG images (*.jpg *.jpeg);;All files (*.*)",
    )
    if not file_paths:
        return []
    paths = [Path(file_path) for file_path in file_paths]
    invalid = [path for path in paths if path.suffix.lower() not in SUPPORTED_EXTENSIONS]
    if invalid:
        QMessageBox.critical(parent, APP_NAME, "Only JPG and JPEG files are supported.")
        return []
    save_settings({"last_image_dir": str(paths[0].parent)})
    return paths
