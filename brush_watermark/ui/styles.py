PANEL = "#111827"
BORDER = "#374151"


def app_stylesheet() -> str:
    return f"""
    QMainWindow, QWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
        background: {PANEL};
        color: #e5e7eb;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 11px;
    }}
    QFrame#Card {{
        background: {PANEL};
        border: none;
    }}
    QLabel {{
        background: transparent;
    }}
    QLabel#SectionTitle {{
        font-size: 11px;
        font-weight: 700;
        color: #d1d5db;
        padding-bottom: 4px;
        border-bottom: 1px solid {BORDER};
    }}
    QLabel#FieldLabel {{
        color: #9ca3af;
        font-size: 11px;
    }}
    QLabel#HintLabel {{
        color: #6b7280;
        font-size: 10px;
    }}
    QLineEdit, QComboBox, QListWidget, QPushButton {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 5px;
        color: #f9fafb;
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
        width: 16px;
        background: {PANEL};
        border-left: 1px solid {BORDER};
    }}
    QComboBox::down-arrow {{
        width: 8px;
        height: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {PANEL};
        color: #f9fafb;
        border: 1px solid {BORDER};
        selection-background-color: #2563eb;
        selection-color: white;
    }}
    QLineEdit:focus, QComboBox:focus, QListWidget:focus {{
        border: 1px solid #60a5fa;
    }}
    QListWidget {{
        padding: 4px;
    }}
    QListWidget::item {{
        background: transparent;
        padding: 4px 6px;
        border-radius: 4px;
        font-size: 11px;
    }}
    QListWidget::item:selected {{
        background: #2563eb;
        color: white;
    }}
    QPushButton {{
        padding: 4px 8px;
        min-height: 24px;
    }}
    QPushButton:hover {{
        border-color: #6b7280;
    }}
    QPushButton#PrimaryButton {{
        background: #2563eb;
        color: white;
        border: 1px solid #2563eb;
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
        background: #1d4ed8;
        border-color: #1d4ed8;
    }}
    QScrollArea {{
        border: none;
    }}
    QCheckBox {{
        spacing: 6px;
        font-size: 11px;
        background: transparent;
    }}
    QSlider {{
        background: transparent;
    }}
    QSlider::groove:horizontal {{
        border: 0;
        height: 4px;
        background: {BORDER};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: #60a5fa;
        border: 0;
        width: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }}
    """
