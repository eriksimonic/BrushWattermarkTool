"""Right-hand inspector: watermark, brush, auto watermark, layers and export settings.

Keeps the old SidebarPanel's settings API so MainWindow's editing logic is
unchanged; tools, saving, preview mode, zoom and version info live in the top
bar, tool rail, canvas overlays and footer instead.
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from brush_watermark.models import Settings, Stroke
from brush_watermark.rendering.blend import BLEND_MODE_CHOICES
from brush_watermark.rendering.fonts import available_font_names
from brush_watermark.services.auto_watermark import DEFAULT_DENSITY, MAX_DENSITY, MIN_DENSITY
from brush_watermark.ui.color_picker import ColorSwatchPicker
from brush_watermark.ui.controls import Chip, CollapsibleSection, KeyBadge, SliderRow, Stepper, SwitchRow
from brush_watermark.ui.design_tokens import DANGER_TEXT, TEXT
from brush_watermark.ui.icons import get_icon
from brush_watermark.ui.layer_list import LayerItem, LayerList

INSPECTOR_WIDTH = 340


class InspectorPanel(QFrame):
    document_settings_changed = Signal()
    stroke_controls_changed = Signal()
    layer_item_clicked = Signal(int)
    layer_visibility_toggled = Signal(int)
    delete_selected = Signal()
    delete_all = Signal()
    guide_suppress_changed = Signal(bool)
    auto_place_requested = Signal(int)

    def __init__(self, settings: Settings, swatch_colors: list[str]):
        super().__init__()
        self.setObjectName("InspectorPanel")
        # 1 px border + 8 px scrollbar + 1 px slack inside the INSPECTOR_WIDTH scroll area.
        self.setFixedWidth(INSPECTOR_WIDTH - 10)
        self._build_ui(settings, swatch_colors)
        self._connect_signals()
        self.load_tool_defaults(settings)

    # ---- construction -------------------------------------------------

    def _build_ui(self, settings: Settings, swatch_colors: list[str]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        watermark = CollapsibleSection("Watermark", icon_name="stamp")
        self.watermark_text_edit = QLineEdit(settings.watermark_text)
        self.watermark_text_edit.setPlaceholderText("Watermark text")
        self.watermark_text_edit.setAccessibleName("Watermark text")
        self.font_combo = QComboBox()
        self.font_combo.setAccessibleName("Font")
        font_names = available_font_names()
        self.font_combo.addItems(font_names)
        if settings.font_name in font_names:
            self.font_combo.setCurrentText(settings.font_name)
        elif font_names:
            self.font_combo.setCurrentIndex(0)
        self.font_px_chip = QLabel()
        self.font_px_chip.setObjectName("ValueChip")
        self.font_px_chip.setToolTip("Font size follows brush size")
        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_row.addWidget(self.font_combo, 1)
        font_row.addWidget(self.font_px_chip)
        self.auto_fit_check = SwitchRow("Auto-fit text to stroke", settings.auto_fit_text)
        self.repeat_text_check = SwitchRow("Repeat along stroke", settings.repeat_text, switch_first=True)
        self.repeat_spacing_spin = Stepper(0, 50, settings.repeat_spacing, prefix="gap")
        self.repeat_spacing_spin.setToolTip("Space between repeats, in character widths")
        repeat_row = QHBoxLayout()
        repeat_row.setSpacing(8)
        repeat_row.addWidget(self.repeat_text_check, 1)
        repeat_row.addWidget(self.repeat_spacing_spin)
        watermark.body_layout.addWidget(self.watermark_text_edit)
        watermark.body_layout.addLayout(font_row)
        watermark.body_layout.addWidget(self.auto_fit_check)
        watermark.body_layout.addLayout(repeat_row)
        # The camera/settings strip is kept in the always-open Watermark section
        # so it's visible without expanding Export.
        self.add_metadata_check = SwitchRow("Visible metadata strip", settings.add_visible_metadata)
        self.add_metadata_check.setToolTip(
            "Expand the saved copy with camera, lens, settings, serial, and copy info at the bottom."
        )
        self.metadata_copy_edit = QLineEdit(settings.metadata_copy_text)
        self.metadata_copy_edit.setPlaceholderText("Additional copy info (optional)")
        self.metadata_copy_edit.setAccessibleName("Additional copy info")
        watermark.body_layout.addWidget(self.add_metadata_check)
        watermark.body_layout.addWidget(self.metadata_copy_edit)
        layout.addWidget(watermark)

        self.brush_section = CollapsibleSection("Brush", icon_name="paintbrush")
        self.brush_section.body_layout.setSpacing(14)
        self.color_picker = ColorSwatchPicker()
        self.color_picker.set_swatches(swatch_colors, settings.text_color)
        self.blend_combo = QComboBox()
        self.blend_combo.setAccessibleName("Blend mode")
        for mode_key, mode_label in BLEND_MODE_CHOICES:
            self.blend_combo.addItem(mode_label, mode_key)
        self.opacity_row = SliderRow("Strength", 1, 100, settings.opacity)
        self.auto_strength_check = Chip("Auto", icon_name="wand-2")
        self.auto_strength_check.setChecked(settings.auto_strength)
        self.auto_strength_check.setToolTip(
            "Compute each new stroke's strength from the pixels underneath it — "
            "flat areas get a fainter mark, busy/textured areas can hide a stronger one. "
            "Applies when a stroke is first drawn or auto-placed."
        )
        self.opacity_row.add_header_widget(self.auto_strength_check)
        self.brush_row = SliderRow("Size", 5, 600, settings.brush_size)
        self.softness_row = SliderRow("Softness", 0, 20, settings.mask_softness)
        body = self.brush_section.body_layout
        body.addWidget(self.color_picker)
        body.addLayout(self._labeled_row("Blend", self.blend_combo))
        body.addWidget(self.opacity_row)
        body.addWidget(self.brush_row)
        body.addWidget(self.softness_row)
        layout.addWidget(self.brush_section)

        auto = CollapsibleSection("Auto watermark", icon_name="wand-2")
        self.auto_density_row = SliderRow("Density", MIN_DENSITY, MAX_DENSITY, DEFAULT_DENSITY)
        self.auto_place_btn = QPushButton("Auto-place")
        self.auto_place_btn.setObjectName("SecondaryButton")
        self.auto_place_btn.setIcon(get_icon("wand-2", 15, TEXT))
        self.auto_place_btn.setIconSize(QSize(15, 15))
        self.auto_place_btn.setToolTip(
            "Find busy, detail-rich areas that avoid the photo's focal subject "
            "and drop several faint, low-opacity watermarks there."
        )
        auto_row = QHBoxLayout()
        auto_row.setSpacing(12)
        auto_row.addWidget(self.auto_density_row, 1)
        auto_row.addWidget(self.auto_place_btn)
        self.auto_watermark_status_label = QLabel()
        self.auto_watermark_status_label.setObjectName("HintLabel")
        self.auto_watermark_status_label.setWordWrap(True)
        self.auto_watermark_status_label.hide()
        auto.body_layout.addLayout(auto_row)
        auto.body_layout.addWidget(self.auto_watermark_status_label)
        layout.addWidget(auto)

        self.layers_section = CollapsibleSection("Layers", icon_name="layers")
        self.layer_count_badge = QLabel("0")
        self.layer_count_badge.setObjectName("CountBadge")
        self.layer_count_badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.layers_section.add_header_widget(self.layer_count_badge)
        self.layer_list = LayerList()
        self.delete_selected_btn = QPushButton("Delete")
        self.delete_selected_btn.setObjectName("SecondaryButton")
        self.delete_selected_btn.setIcon(get_icon("trash-2", 13, TEXT))
        self.delete_selected_btn.setToolTip("Delete the selected layer (Del)")
        # The badge sits in the button's right padding (QSS [keyBadge="true"]).
        self.delete_selected_btn.setProperty("keyBadge", True)
        delete_badge_row = QHBoxLayout(self.delete_selected_btn)
        delete_badge_row.setContentsMargins(0, 0, 8, 0)
        delete_badge_row.addStretch(1)
        self.delete_key_badge = KeyBadge("Del")
        self.delete_key_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        delete_badge_row.addWidget(self.delete_key_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        self.delete_all_btn = QPushButton("Clear all")
        self.delete_all_btn.setObjectName("DangerButton")
        self.delete_all_btn.setIcon(get_icon("trash", 13, DANGER_TEXT))
        layer_actions = QHBoxLayout()
        layer_actions.setSpacing(6)
        layer_actions.addWidget(self.delete_selected_btn, 1)
        layer_actions.addWidget(self.delete_all_btn, 1)
        self.layers_section.body_layout.setSpacing(8)
        self.layers_section.body_layout.addWidget(self.layer_list)
        self.layers_section.body_layout.addLayout(layer_actions)
        layout.addWidget(self.layers_section)

        export = CollapsibleSection("Export", icon_name="image", expanded=False)
        self.reveal_in_explorer_check = SwitchRow("Show in Explorer after save", True)
        export.body_layout.addWidget(self.reveal_in_explorer_check)
        layout.addWidget(export)

        layout.addStretch(1)

    @staticmethod
    def _labeled_row(text: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        label.setFixedWidth(64)
        row.addWidget(label)
        row.addWidget(widget, 1)
        return row

    def _connect_signals(self):
        emit_document = lambda *_: self.document_settings_changed.emit()
        emit_controls = lambda *_: self.stroke_controls_changed.emit()

        self.watermark_text_edit.textChanged.connect(emit_document)
        self.font_combo.currentTextChanged.connect(emit_document)
        self.auto_fit_check.toggled.connect(emit_document)
        self.auto_strength_check.toggled.connect(emit_document)
        self.auto_strength_check.toggled.connect(self._update_opacity_enabled)
        self.add_metadata_check.toggled.connect(emit_document)
        self.add_metadata_check.toggled.connect(self._update_metadata_copy_visible)
        self.metadata_copy_edit.textChanged.connect(emit_document)

        self.color_picker.color_changed.connect(emit_controls)
        self.blend_combo.currentIndexChanged.connect(emit_controls)
        self.opacity_row.slider.valueChanged.connect(emit_controls)
        self.brush_row.slider.valueChanged.connect(emit_controls)
        self.softness_row.slider.valueChanged.connect(emit_controls)
        self.repeat_text_check.toggled.connect(emit_controls)
        self.repeat_text_check.toggled.connect(self._update_repeat_spacing_enabled)
        self.repeat_spacing_spin.valueChanged.connect(emit_controls)

        self.auto_density_row.slider.valueChanged.connect(
            lambda v: self.auto_density_row.set_value_text(str(v))
        )
        self.auto_density_row.set_value_text(str(self.density()))
        self.auto_place_btn.clicked.connect(lambda _checked=False: self.auto_place_requested.emit(self.density()))

        for row in (self.opacity_row, self.brush_row):
            row.slider.dragStarted.connect(lambda: self.guide_suppress_changed.emit(True))
            row.slider.dragEnded.connect(lambda: self.guide_suppress_changed.emit(False))

        self.layer_list.layer_clicked.connect(self.layer_item_clicked.emit)
        self.layer_list.visibility_toggled.connect(self.layer_visibility_toggled.emit)
        self.delete_selected_btn.clicked.connect(lambda _checked=False: self.delete_selected.emit())
        self.delete_all_btn.clicked.connect(lambda _checked=False: self.delete_all.emit())
        self._update_repeat_spacing_enabled()
        self._update_opacity_enabled()
        self._update_metadata_copy_visible()

    # ---- state ---------------------------------------------------------

    def _update_metadata_copy_visible(self, *_):
        self.metadata_copy_edit.setVisible(self.add_metadata_check.isChecked())

    def _update_repeat_spacing_enabled(self, *_):
        self.repeat_spacing_spin.setEnabled(self.repeat_text_check.isChecked())

    def _update_opacity_enabled(self, *_):
        # Only the slider: the Auto chip lives in the same row and must stay clickable.
        self.opacity_row.slider.setEnabled(not self.auto_strength_check.isChecked())

    def density(self) -> int:
        return int(self.auto_density_row.slider.value())

    def set_swatches(self, colors: list[str], selected: str) -> None:
        self.color_picker.set_swatches(colors, selected)

    def set_brush_context(self, *, layer_name: str | None = None, visible: bool = True):
        if layer_name is None:
            self.brush_section.set_title("Brush")
            return
        title = f"Layer · {layer_name}"
        if not visible:
            title += " · hidden"
        self.brush_section.set_title(title)

    def set_font_px(self, pixel_size: int) -> None:
        self.font_px_chip.setText(f"{pixel_size} px")

    def set_delete_enabled(self, enabled: bool) -> None:
        self.delete_selected_btn.setEnabled(enabled)

    def set_layers(self, items: list[LayerItem], selected: int = -1) -> None:
        self.layer_count_badge.setText(str(len(items)))
        self.layer_list.set_layers(items, selected)

    def set_selected_layer(self, index: int) -> None:
        self.layer_list.set_selected(index)

    def _block_control_signals(self, block: bool):
        for widget in (
            self.color_picker,
            self.blend_combo,
            self.opacity_row.slider,
            self.brush_row.slider,
            self.softness_row.slider,
            self.repeat_text_check,
            self.repeat_spacing_spin,
        ):
            widget.blockSignals(block)

    def _load_control_values(self, source: Settings | Stroke):
        """Push brush/opacity/softness/repeat/color/blend from a Settings or Stroke onto the controls."""
        self._block_control_signals(True)
        self.brush_row.slider.setValue(source.brush_size)
        self.opacity_row.slider.setValue(source.opacity)
        self.softness_row.slider.setValue(source.mask_softness)
        self.repeat_text_check.setChecked(source.repeat_text)
        self.repeat_spacing_spin.setValue(source.repeat_spacing)
        self.color_picker.set_selected(source.text_color)
        blend_index = self.blend_combo.findData(source.blend_mode)
        if blend_index >= 0:
            self.blend_combo.setCurrentIndex(blend_index)
        self._block_control_signals(False)
        self._update_repeat_spacing_enabled()

    def load_document_settings(self, settings: Settings) -> None:
        """Show one image's document-level settings (text, font, auto-fit, strength mode, strip)."""
        widgets = (
            self.watermark_text_edit,
            self.font_combo,
            self.auto_fit_check,
            self.auto_strength_check,
            self.add_metadata_check,
            self.metadata_copy_edit,
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.watermark_text_edit.setText(settings.watermark_text)
        if self.font_combo.findText(settings.font_name) >= 0:
            self.font_combo.setCurrentText(settings.font_name)
        self.auto_fit_check.setChecked(settings.auto_fit_text)
        self.auto_strength_check.setChecked(settings.auto_strength)
        self.add_metadata_check.setChecked(settings.add_visible_metadata)
        self.metadata_copy_edit.setText(settings.metadata_copy_text)
        for widget in widgets:
            widget.blockSignals(False)
        self._update_opacity_enabled()
        self._update_metadata_copy_visible()

    def load_tool_defaults(self, settings: Settings):
        self._load_control_values(settings)
        self.set_brush_context()

    def load_stroke_controls(self, stroke: Stroke):
        self._load_control_values(stroke)
        self.set_brush_context(layer_name=stroke.name, visible=stroke.visible)

    def read_document_settings(self, tool_defaults: Settings) -> Settings:
        return Settings(
            watermark_text=self.watermark_text_edit.text(),
            opacity=tool_defaults.opacity,
            font_name=self.font_combo.currentText(),
            brush_size=tool_defaults.brush_size,
            angle_offset=tool_defaults.angle_offset,
            mask_softness=tool_defaults.mask_softness,
            text_color=tool_defaults.text_color,
            auto_fit_text=bool(self.auto_fit_check.isChecked()),
            auto_strength=bool(self.auto_strength_check.isChecked()),
            repeat_text=tool_defaults.repeat_text,
            repeat_spacing=tool_defaults.repeat_spacing,
            blend_mode=tool_defaults.blend_mode,
            add_visible_metadata=bool(self.add_metadata_check.isChecked()),
            metadata_copy_text=self.metadata_copy_edit.text(),
        )

    def read_stroke_controls(self) -> dict:
        return {
            "brush_size": int(self.brush_row.slider.value()),
            "opacity": int(self.opacity_row.slider.value()),
            "blend_mode": str(self.blend_combo.currentData()),
            "text_color": self.color_picker.selected_color(),
            "angle_offset": 0,
            "mask_softness": int(self.softness_row.slider.value()),
            "repeat_text": bool(self.repeat_text_check.isChecked()),
            "repeat_spacing": int(self.repeat_spacing_spin.value()),
        }

    def read_tool_defaults(self) -> dict:
        return self.read_stroke_controls()

    def set_auto_watermark_running(self, running: bool):
        self.auto_place_btn.setEnabled(not running)
        self.auto_density_row.setEnabled(not running)
        if running:
            self.set_auto_watermark_status("Analyzing photo…")

    def set_auto_watermark_status(self, text: str):
        self.auto_watermark_status_label.setText(text)
        self.auto_watermark_status_label.setVisible(bool(text))
