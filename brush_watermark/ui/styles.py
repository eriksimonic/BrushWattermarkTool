from brush_watermark.ui.design_tokens import (
    BORDER,
    BUTTON_HOVER,
    CANVAS_BG,
    CHROME,
    DIVIDER,
    HANDLE,
    INPUT,
    LINK,
    PANEL,
    SELECTION,
    SELECTION_BORDER,
    TEXT,
    TEXT_MUTED,
    TEXT_SECONDARY,
    TRACK,
)


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
        padding: 0 4px;
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
        border-radius: 3px;
        color: {TEXT};
        font-size: 11px;
    }}
    QLineEdit, QComboBox {{
        padding: 2px 6px;
        min-height: 22px;
        max-height: 22px;
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
        width: 8px;
        height: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {INPUT};
        color: {TEXT};
        border: 1px solid {BORDER};
        selection-background-color: {SELECTION};
        selection-color: {TEXT};
    }}
    QLineEdit:focus, QComboBox:focus, QListWidget:focus, QSpinBox:focus {{
        border: 1px solid {SELECTION_BORDER};
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
        padding: 1px 4px;
        min-height: 20px;
        max-height: 20px;
    }}
    QPushButton {{
        padding: 3px 8px;
        min-height: 22px;
        max-height: 22px;
        background: {INPUT};
    }}
    QPushButton:hover {{
        background: {BUTTON_HOVER};
        border-color: {SELECTION_BORDER};
    }}
    QPushButton#PrimaryButton {{
        background: {SELECTION};
        color: {TEXT};
        border: 1px solid {BORDER};
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
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
    QCheckBox {{
        spacing: 8px;
        font-size: 11px;
        color: {TEXT_SECONDARY};
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {BORDER};
        border-radius: 2px;
        background: {INPUT};
    }}
    QCheckBox::indicator:checked {{
        background: {HANDLE};
        border-color: {SELECTION_BORDER};
    }}
    QSlider::groove:horizontal {{
        border: 0;
        height: 2px;
        background: {TRACK};
    }}
    QSlider::handle:horizontal {{
        background: {HANDLE};
        border: 0;
        width: 10px;
        margin: -6px 0;
        border-radius: 5px;
    }}
    """
