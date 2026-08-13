from brush_watermark.ui.design_tokens import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_PRESSED,
    BORDER,
    BUTTON_HOVER,
    CANVAS_BG,
    CHROME,
    DIVIDER,
    INPUT,
    LINK,
    ON_ACCENT,
    PANEL,
    SELECTION,
    SELECTION_BORDER,
    TEXT,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from brush_watermark.ui.icons import ICONS_DIR

_CHEVRON_DOWN_PNG = (ICONS_DIR / "chevron-down-static.png").as_posix()
_CHEVRON_UP_PNG = (ICONS_DIR / "chevron-up-static.png").as_posix()


def app_stylesheet() -> str:
    return f"""
    QMainWindow {{
        background: {CHROME};
        color: {TEXT};
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11px;
    }}
    QWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
        background: {PANEL};
        color: {TEXT};
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11px;
    }}
    QLabel {{
        background: transparent;
    }}
    QLabel#SectionHeader {{
        font-size: 11px;
        font-weight: 600;
        color: {TEXT_SECONDARY};
        padding: 0 2px;
    }}
    QFrame#SectionDivider {{
        background: {DIVIDER};
        max-height: 1px;
        min-height: 1px;
        border: none;
    }}
    QLabel#FieldLabel {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
    }}
    QLabel#SliderName {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
    }}
    QLabel#SliderValue {{
        color: {TEXT};
        font-size: 11px;
        min-width: 48px;
    }}
    QLabel#HintLabel {{
        color: {TEXT_MUTED};
        font-size: 10px;
    }}
    QLabel#HintLabel a {{
        color: {LINK};
        text-decoration: none;
    }}
    QLabel#HintLabel a:hover {{
        text-decoration: underline;
    }}
    QLineEdit, QComboBox, QListWidget, QSpinBox, QPushButton {{
        background: {INPUT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        color: {TEXT};
        font-size: 11px;
    }}
    QLineEdit, QComboBox {{
        padding: 4px 10px;
        min-height: 24px;
        max-height: 24px;
    }}
    QComboBox {{
        padding-right: 4px;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 18px;
        background: {INPUT};
        border-left: 1px solid {BORDER};
    }}
    QComboBox::down-arrow {{
        width: 10px;
        height: 10px;
        image: url({_CHEVRON_DOWN_PNG});
    }}
    QComboBox QAbstractItemView {{
        background: {INPUT};
        color: {TEXT};
        border: 1px solid {BORDER};
        selection-background-color: {SELECTION};
        selection-color: {TEXT};
    }}
    QLineEdit:focus, QComboBox:focus, QListWidget:focus, QSpinBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QListWidget {{
        padding: 2px;
        background: {INPUT};
    }}
    QListWidget::item {{
        background: transparent;
        padding: 3px 6px;
        border-radius: 2px;
        font-size: 11px;
    }}
    QListWidget::item:selected {{
        background: {SELECTION};
        color: {TEXT};
        border-left: 2px solid {SELECTION_BORDER};
    }}
    QSpinBox {{
        padding: 2px 6px;
        min-height: 22px;
        max-height: 22px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        subcontrol-origin: border;
        width: 14px;
        background: transparent;
        border: none;
    }}
    QSpinBox::up-button {{
        subcontrol-position: top right;
        margin-top: 1px;
    }}
    QSpinBox::down-button {{
        subcontrol-position: bottom right;
        margin-bottom: 1px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background: {BUTTON_HOVER};
        border-radius: 3px;
    }}
    QSpinBox::up-arrow {{
        width: 8px;
        height: 8px;
        image: url({_CHEVRON_UP_PNG});
    }}
    QSpinBox::down-arrow {{
        width: 8px;
        height: 8px;
        image: url({_CHEVRON_DOWN_PNG});
    }}
    QPushButton {{
        padding: 5px 12px;
        min-height: 24px;
        max-height: 24px;
        background: {INPUT};
    }}
    QPushButton:hover {{
        background: {BUTTON_HOVER};
        border-color: {SELECTION_BORDER};
    }}
    QPushButton#PrimaryButton {{
        background: {ACCENT};
        color: {ON_ACCENT};
        border: 1px solid {ACCENT};
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
        background: {ACCENT_HOVER};
        border-color: {ACCENT_HOVER};
    }}
    QPushButton#PrimaryButton:pressed {{
        background: {ACCENT_PRESSED};
        border-color: {ACCENT_PRESSED};
    }}
    QPushButton#ToolBtn {{
        padding: 0px;
        border-radius: 5px;
    }}
    QPushButton#ToolBtn:checked {{
        background: {ACCENT};
        border: 1px solid {ACCENT_PRESSED};
    }}
    QPushButton#ToolBtn:hover {{
        background: {BUTTON_HOVER};
        border-color: {SELECTION_BORDER};
    }}
    QPushButton#ChipButton {{
        padding: 2px 10px;
        min-height: 20px;
        max-height: 20px;
        border-radius: 10px;
    }}
    QPushButton#ChipButton:checked {{
        background: {ACCENT};
        color: {ON_ACCENT};
        border: 1px solid {ACCENT_PRESSED};
    }}
    QPushButton#ChipButton:hover {{
        background: {BUTTON_HOVER};
        border-color: {SELECTION_BORDER};
    }}
    QScrollArea {{
        border: none;
        background: {PANEL};
    }}
    QScrollBar:horizontal {{
        height: 0px;
    }}
    QScrollBar:vertical {{
        width: 8px;
        background: {PANEL};
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollArea#CanvasScrollArea, QScrollArea#CanvasScrollArea > QWidget > QWidget {{
        background: {CANVAS_BG};
    }}
    QScrollArea#CanvasScrollArea QScrollBar:horizontal {{
        height: 8px;
        background: {PANEL};
    }}
    QScrollArea#CanvasScrollArea QScrollBar::handle:horizontal {{
        background: {BORDER};
        min-width: 24px;
        border-radius: 4px;
    }}
    QScrollArea#CanvasScrollArea QScrollBar::add-line:horizontal, QScrollArea#CanvasScrollArea QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QScrollArea#FilmstripArea, QScrollArea#FilmstripArea > QWidget > QWidget {{
        background: {CANVAS_BG};
        border-top: 1px solid {DIVIDER};
    }}
    QScrollArea#FilmstripArea QScrollBar:horizontal {{
        height: 8px;
        background: {CANVAS_BG};
    }}
    QScrollArea#FilmstripArea QScrollBar::handle:horizontal {{
        background: {BORDER};
        min-width: 24px;
        border-radius: 4px;
    }}
    QScrollArea#FilmstripArea QScrollBar::add-line:horizontal, QScrollArea#FilmstripArea QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QCheckBox {{
        spacing: 8px;
        font-size: 11px;
        color: {TEXT_SECONDARY};
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: none;
        background: transparent;
        image: none;
    }}
    """
