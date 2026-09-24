"""Shared fixtures. Qt widgets are tested offscreen (no window server needed)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    from brush_watermark.ui.app_fonts import register_app_fonts

    app = QApplication.instance() or QApplication([])
    register_app_fonts()
    return app
