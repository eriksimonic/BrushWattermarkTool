from brush_watermark.ui.app_fonts import mono_family, ui_family
from brush_watermark.ui.design_tokens import (
    ACCENT,
    ACCENT_BRIGHT,
    ACCENT_HOVER,
    ACCENT_TEXT,
    BORDER,
    BORDER_STRONG,
    CANVAS_BG,
    CHROME,
    DANGER_TEXT,
    DIVIDER,
    FOOTER_BG,
    KEY_BADGE_BORDER,
    ON_ACCENT,
    SURFACE_INPUT,
    SURFACE_MENU,
    SURFACE_RAISED,
    SURFACE_RAISED_HOVER,
    SURFACE_SEGMENT,
    SURFACE_SEGMENT_ON,
    TEXT,
    TEXT_BODY,
    TEXT_FAINT,
    TEXT_LABEL,
    TEXT_MUTED,
    TEXT_SECONDARY,
    WARNING,
    rgba,
)
from brush_watermark.ui.icons import ICONS_DIR

_CHEVRON_DOWN_PNG = (ICONS_DIR / "chevron-down-static.png").as_posix()


def app_stylesheet() -> str:
    ui = ui_family()
    mono = mono_family()
    accent_tint = rgba(ACCENT_BRIGHT, 0.16)
    return f"""
    QWidget {{ color: {TEXT}; font-family: '{ui}'; font-size: 13px; }}
    QMainWindow, QWidget#AppRoot {{ background: {CANVAS_BG}; }}
    QDialog, QMessageBox {{ background: {CHROME}; }}
    QLabel {{ background: transparent; }}
    QToolTip {{
        background: {SURFACE_MENU}; color: {TEXT}; border: 1px solid {BORDER_STRONG};
        border-radius: 6px; padding: 4px 8px; font-size: 12px;
    }}

    /* ---- Areas ---- */
    QFrame#TopBar {{ background: {CHROME}; border: none; border-bottom: 1px solid {DIVIDER}; }}
    QFrame#ToolRail {{ background: {CHROME}; border: none; border-right: 1px solid {DIVIDER}; }}
    QScrollArea#InspectorScroll {{ background: {CHROME}; border: none; border-left: 1px solid {DIVIDER}; }}
    QScrollArea#InspectorScroll > QWidget#qt_scrollarea_viewport {{ background: {CHROME}; }}
    QFrame#InspectorPanel {{ background: {CHROME}; border: none; }}
    QFrame#InspectorSection {{ background: transparent; border: none; border-bottom: 1px solid {DIVIDER}; }}
    QFrame#StatusFooter {{ background: {FOOTER_BG}; border: none; border-top: 1px solid {DIVIDER}; }}
    QFrame#Filmstrip {{ background: {CHROME}; border: none; border-top: 1px solid {DIVIDER}; }}
    QScrollArea#FilmstripScroll, QScrollArea#FilmstripScroll > QWidget#qt_scrollarea_viewport {{
        background: transparent; border: none;
    }}
    QWidget#FilmstripItems {{ background: transparent; }}
    QScrollArea#CanvasScrollArea, QScrollArea#CanvasScrollArea > QWidget#qt_scrollarea_viewport {{
        background: {CANVAS_BG}; border: none;
    }}
    QFrame#FloatingPanel {{ background: {rgba(CHROME, 0.92)}; border: 1px solid {BORDER}; border-radius: 10px; }}
    QFrame#PopupPanel {{ background: {SURFACE_MENU}; border: 1px solid {BORDER_STRONG}; border-radius: 10px; }}
    QFrame#TopDivider, QFrame#RailDivider, QFrame#FooterDivider, QFrame#PillDivider {{
        background: {BORDER}; border: none;
    }}

    /* ---- Text roles ---- */
    QLabel#LogoMark {{ background: {ACCENT}; border-radius: 8px; }}
    QLabel#FileName {{ font-weight: 500; }}
    QLabel#SerialChip {{
        font-family: '{mono}'; font-size: 11px; font-weight: 500; color: {TEXT_SECONDARY};
        border: 1px solid {BORDER}; border-radius: 6px; padding: 2px 7px;
    }}
    QLabel#CountBadge {{
        font-family: '{mono}'; font-size: 11px; font-weight: 500; color: {TEXT_LABEL};
        background: {SURFACE_RAISED}; border-radius: 5px; padding: 1px 6px;
    }}
    QLabel#UnsavedDot {{ background: {WARNING}; border-radius: 3px; }}
    QLabel#UnsavedLabel {{ color: {WARNING}; font-size: 11px; }}
    QLabel#SectionTitle {{ font-weight: 600; }}
    QLabel#SliderName, QLabel#FieldLabel {{ color: {TEXT_LABEL}; font-size: 12px; }}
    QLabel#SliderValue {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; }}
    QLabel#SwitchLabel {{ color: {TEXT_BODY}; }}
    QLabel#HintLabel {{ color: {TEXT_MUTED}; font-size: 11px; }}
    QLabel#HintLabel a, QLabel#FooterText a {{ color: {ACCENT_TEXT}; text-decoration: none; }}
    QLabel#HintTool {{ color: {ACCENT_TEXT}; font-size: 12px; font-weight: 600; }}
    QLabel#HintText {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
    QLabel#ValueChip {{
        font-family: '{mono}'; font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY};
        background: {SURFACE_INPUT}; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 0 10px; min-height: 32px; max-height: 32px;
    }}
    QLabel#KeyBadge {{
        font-family: '{mono}'; font-size: 11px; font-weight: 500; color: {TEXT_SECONDARY};
        background: {SURFACE_MENU}; border: 1px solid {KEY_BADGE_BORDER}; border-bottom-width: 2px;
        border-radius: 4px; padding: 0 5px;
    }}
    QLabel#FooterText {{ color: {TEXT_LABEL}; font-size: 11px; }}
    QLabel#ZoomPercent {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; }}
    QLabel#ReadoutText {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; color: {TEXT_SECONDARY}; }}
    QLabel#ReadoutSlash {{ font-family: '{mono}'; font-size: 12px; color: {TEXT_FAINT}; }}
    QLabel#FilmstripTitle {{ font-size: 12px; font-weight: 600; }}
    QLabel#LayerName {{ font-weight: 500; }}
    QLabel#LayerMeta {{ color: {TEXT_LABEL}; font-size: 11px; }}
    QLabel#LayerName[layerHidden="true"], QLabel#LayerMeta[layerHidden="true"] {{ color: {TEXT_FAINT}; }}
    QLabel#LayerIcon {{ background: {SURFACE_RAISED}; border-radius: 6px; }}
    QLabel#StepperValue {{ font-family: '{mono}'; font-size: 12px; font-weight: 500; }}

    /* ---- Inputs ---- */
    QLineEdit, QComboBox {{
        background: {SURFACE_INPUT}; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 0 10px; min-height: 32px; max-height: 32px; color: {TEXT};
        selection-background-color: {ACCENT};
    }}
    QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT_BRIGHT}; }}
    QComboBox {{ padding-right: 30px; }}
    QComboBox::drop-down {{
        subcontrol-origin: padding; subcontrol-position: center right; width: 28px;
        border: none; background: transparent;
    }}
    QComboBox::down-arrow {{ width: 10px; height: 10px; image: url({_CHEVRON_DOWN_PNG}); }}
    QComboBox QAbstractItemView {{
        background: {SURFACE_MENU}; border: 1px solid {BORDER_STRONG}; padding: 4px; outline: none;
        selection-background-color: {SURFACE_RAISED_HOVER}; selection-color: {TEXT};
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        background: transparent; color: {TEXT}; border: 1px solid transparent; border-radius: 8px;
        padding: 0 12px; min-height: 30px; max-height: 30px; font-weight: 500;
    }}
    QPushButton:hover {{ background: {DIVIDER}; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; }}
    QPushButton#SecondaryButton, QPushButton#DangerButton {{ background: {SURFACE_RAISED}; border-color: {BORDER_STRONG}; }}
    QPushButton#SecondaryButton:hover, QPushButton#DangerButton:hover {{ background: {SURFACE_RAISED_HOVER}; }}
    QPushButton#DangerButton {{ color: {DANGER_TEXT}; }}
    QPushButton#GhostButton {{ color: {TEXT_SECONDARY}; }}
    QPushButton#PrimaryButton, QPushButton#SplitMain, QPushButton#SplitArrow {{
        background: {ACCENT}; color: {ON_ACCENT}; border: none;
    }}
    QPushButton#PrimaryButton:hover, QPushButton#SplitMain:hover, QPushButton#SplitArrow:hover {{
        background: {ACCENT_HOVER};
    }}
    QPushButton#SplitMain {{ border-top-right-radius: 0; border-bottom-right-radius: 0; padding: 0 14px; }}
    QPushButton#SplitArrow {{
        border-top-left-radius: 0; border-bottom-left-radius: 0;
        border-left: 1px solid {rgba(ON_ACCENT, 0.22)}; padding: 0 8px;
    }}
    QPushButton#MenuButton {{
        color: {TEXT_SECONDARY}; border-radius: 6px; padding: 0 9px;
        min-height: 26px; max-height: 26px; font-weight: 400;
    }}
    QPushButton#MenuButton::menu-indicator {{ image: none; width: 0px; }}
    QFrame#SegmentedControl {{ background: {SURFACE_SEGMENT}; border: 1px solid {BORDER}; border-radius: 9px; }}
    QPushButton#Segment {{
        color: {TEXT_LABEL}; border: none; border-radius: 6px; padding: 0 12px;
        min-height: 26px; max-height: 26px; font-size: 12px;
    }}
    QPushButton#Segment:checked {{ background: {SURFACE_SEGMENT_ON}; color: {TEXT}; }}
    QPushButton#Chip {{
        color: {TEXT_LABEL}; border: 1px solid {BORDER_STRONG}; border-radius: 6px; padding: 0 8px;
        min-height: 22px; max-height: 22px; font-size: 11px;
    }}
    QPushButton#Chip:checked {{ background: {accent_tint}; border-color: {rgba(ACCENT_BRIGHT, 0.5)}; color: {ACCENT_TEXT}; }}
    QFrame#Stepper {{ background: {SURFACE_INPUT}; border: 1px solid {BORDER}; border-radius: 8px; }}
    QPushButton#StepButton {{ border: none; border-radius: 0; padding: 0; min-height: 28px; max-height: 28px; }}
    QPushButton#StepButton:hover {{ background: {SURFACE_RAISED_HOVER}; }}
    QPushButton#PillButton, QPushButton#PillButtonMono {{
        color: {TEXT_SECONDARY}; padding: 0 9px; min-height: 28px; max-height: 28px; font-size: 12px;
    }}
    QPushButton#PillButtonMono {{ font-family: '{mono}'; }}
    QPushButton#PillButton:checked, QPushButton#PillButtonMono:checked {{ background: {accent_tint}; color: {ACCENT_TEXT}; }}
    QPushButton#LayerEye {{ padding: 0; min-height: 28px; max-height: 28px; border-radius: 6px; }}
    QPushButton#FooterUpdateButton {{
        background: {ACCENT}; color: {ON_ACCENT}; border: none; border-radius: 5px;
        padding: 0 8px; min-height: 20px; max-height: 20px; font-size: 11px;
    }}
    QPushButton#Swatch {{
        border: 1px solid {rgba(ON_ACCENT, 0.14)}; border-radius: 6px; padding: 0;
        min-height: 22px; max-height: 22px; min-width: 22px; max-width: 22px;
    }}
    QPushButton#Swatch:checked {{ border: 2px solid {ACCENT_BRIGHT}; }}
    QToolButton#RailButton {{ background: transparent; border: 1px solid transparent; border-radius: 10px; }}
    QToolButton#RailButton:hover {{ background: {SURFACE_RAISED}; }}
    QToolButton#RailButton:checked {{ background: {accent_tint}; border-color: {rgba(ACCENT_BRIGHT, 0.45)}; }}

    /* ---- Layers ---- */
    QFrame#LayerRow {{ background: transparent; border: 1px solid transparent; border-radius: 8px; }}
    QFrame#LayerRow:hover {{ background: {SURFACE_INPUT}; }}
    QFrame#LayerRow[selected="true"] {{ background: {rgba(ACCENT_BRIGHT, 0.10)}; border-color: {rgba(ACCENT_BRIGHT, 0.40)}; }}

    /* ---- Menus ---- */
    QMenu {{ background: {SURFACE_MENU}; border: 1px solid {BORDER_STRONG}; border-radius: 10px; padding: 6px; }}
    QMenu::item {{ padding: 8px 14px; border-radius: 6px; color: {TEXT}; background: transparent; }}
    QMenu::item:selected {{ background: {SURFACE_RAISED_HOVER}; }}
    QMenu::item:disabled {{ color: {TEXT_MUTED}; }}
    QMenu::separator {{ height: 1px; background: {BORDER_STRONG}; margin: 4px 2px; }}
    QMenu#SaveMenu {{ min-width: 248px; }}

    /* ---- Scrollbars ---- */
    QScrollBar:vertical {{ width: 8px; background: transparent; margin: 0; }}
    QScrollBar:horizontal {{ height: 8px; background: transparent; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 24px; }}
    QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """
