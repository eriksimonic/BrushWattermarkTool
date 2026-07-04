from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from brush_watermark.models import Settings, Stroke
from brush_watermark.rendering.blend import BLEND_MODE_CHOICES
from brush_watermark.rendering.fonts import font_candidates
from brush_watermark.services.auto_update import can_auto_update
from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.color_picker import ColorSwatchPicker


class SidebarPanel(QWidget):
    document_settings_changed = Signal()
    stroke_controls_changed = Signal()
    layer_selected = Signal(int)
    layer_item_pressed = Signal(int)
    layer_item_clicked = Signal(int)
    delete_selected = Signal()
    delete_all = Signal()
    save_and_close = Signal()
    exit_without_saving = Signal()
    update_now = Signal()

    def __init__(self, settings: Settings, swatch_colors: list[str]):
        super().__init__()
        self._swatch_colors = swatch_colors
        self._build_ui(settings)
        self._connect_signals()
        self.load_tool_defaults(settings)

    def _build_ui(self, settings: Settings):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        watermark_card, watermark_layout = self._make_card("Watermark")
        layout.addWidget(watermark_card)

        self.watermark_text_edit = QLineEdit(settings.watermark_text)
        self.font_combo = QComboBox()
        self.font_combo.addItems(list(font_candidates().keys()))
        self.font_combo.setCurrentText(settings.font_name)
        self.auto_fit_check = QCheckBox("Auto fit text to stroke")
        self.auto_fit_check.setChecked(settings.auto_fit_text)

        self._add_form_row(watermark_layout, "Text", self.watermark_text_edit)
        self._add_form_row(watermark_layout, "Font", self.font_combo)
        watermark_layout.addWidget(self.auto_fit_check)

        stroke_card, stroke_layout = self._make_card("Layers")
        layout.addWidget(stroke_card)

        self.stroke_list = QListWidget()
        self.stroke_list.setFixedHeight(96)
        stroke_layout.addWidget(self.stroke_list)

        layer_actions = QHBoxLayout()
        layer_actions.setSpacing(6)
        layer_actions.setContentsMargins(0, 8, 0, 0)
        self.delete_selected_btn = QPushButton("Delete")
        self.delete_all_btn = QPushButton("Clear all")
        layer_actions.addWidget(self.delete_selected_btn)
        layer_actions.addWidget(self.delete_all_btn)
        layout.addLayout(layer_actions)

        controls_card, controls_layout = self._make_card("Controls")
        layout.addWidget(controls_card)
        self.context_label = QLabel("Tool defaults")
        self.context_label.setObjectName("HintLabel")
        controls_layout.addWidget(self.context_label)

        self.color_picker = ColorSwatchPicker()
        self.color_picker.set_swatches(self._swatch_colors, settings.text_color)
        controls_layout.addWidget(self.color_picker)

        self.blend_combo = QComboBox()
        for mode_key, mode_label in BLEND_MODE_CHOICES:
            self.blend_combo.addItem(mode_label, mode_key)

        self.opacity_value_label = self._make_field_label("Strength")
        self.opacity_slider = self._make_slider(1, 100, settings.opacity)
        self.brush_value_label = self._make_field_label("Brush")
        self.brush_size_slider = self._make_slider(5, 600, settings.brush_size)
        self.font_size_value_label = QLabel()
        self.font_size_value_label.setObjectName("HintLabel")
        self.angle_value_label = self._make_field_label("Angle")
        self.angle_slider = self._make_slider(-20, 20, settings.angle_offset)
        self.softness_value_label = self._make_field_label("Softness")
        self.softness_slider = self._make_slider(0, 20, settings.mask_softness)
        self.repeat_text_check = QCheckBox("Repeat text along stroke")
        self.repeat_text_check.setChecked(settings.repeat_text)
        self.repeat_spacing_spin = QSpinBox()
        self.repeat_spacing_spin.setRange(0, 50)
        self.repeat_spacing_spin.setValue(settings.repeat_spacing)
        self.repeat_spacing_spin.setToolTip("Space between repeats, in character widths")
        self.repeat_spacing_spin.setFixedWidth(56)
        repeat_row = QHBoxLayout()
        repeat_row.setSpacing(8)
        repeat_row.addWidget(self.repeat_text_check, 1)
        repeat_row.addWidget(QLabel("gap"))
        repeat_row.addWidget(self.repeat_spacing_spin)

        self._add_form_row(controls_layout, "Blend", self.blend_combo)
        self._add_slider_row(controls_layout, self.opacity_value_label, self.opacity_slider)
        self._add_slider_row(controls_layout, self.brush_value_label, self.brush_size_slider)
        controls_layout.addWidget(self.font_size_value_label)
        self._add_slider_row(controls_layout, self.angle_value_label, self.angle_slider)
        self._add_slider_row(controls_layout, self.softness_value_label, self.softness_slider)
        controls_layout.addLayout(repeat_row)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        self.reveal_in_explorer_check = QCheckBox("Show in Explorer after save")
        self.reveal_in_explorer_check.setChecked(True)
        actions.addWidget(self.reveal_in_explorer_check)
        self.ok_button = QPushButton("Save and close")
        self.ok_button.setObjectName("PrimaryButton")
        self.exit_button = QPushButton("Exit without saving")
        actions.addWidget(self.ok_button)
        actions.addWidget(self.exit_button)
        layout.addLayout(actions)

        help_card, help_layout = self._make_card("Help")
        layout.addWidget(help_card)
        help_text = QLabel(
            "Paint: left mouse · Select: click watermark · Deselect: click again · "
            "Erase: right mouse · Wheel: strength · Alt+wheel: brush/font size · "
            "Controls edit the selected layer, or tool defaults when nothing is selected."
        )
        help_text.setWordWrap(True)
        help_text.setObjectName("HintLabel")
        help_layout.addWidget(help_text)
        self.version_label = QLabel()
        self.version_label.setObjectName("HintLabel")
        help_layout.addWidget(self.version_label)
        self.update_status_label = QLabel()
        self.update_status_label.setObjectName("HintLabel")
        self.update_status_label.setWordWrap(True)
        self.update_status_label.setOpenExternalLinks(True)
        help_layout.addWidget(self.update_status_label)
        self.update_now_button = QPushButton("Download and install update")
        self.update_now_button.setObjectName("PrimaryButton")
        self.update_now_button.hide()
        help_layout.addWidget(self.update_now_button)
        self.update_progress_label = QLabel()
        self.update_progress_label.setObjectName("HintLabel")
        self.update_progress_label.hide()
        help_layout.addWidget(self.update_progress_label)
        layout.addStretch(1)

    def _connect_signals(self):
        emit_document = lambda *_: self.document_settings_changed.emit()
        emit_controls = lambda *_: self.stroke_controls_changed.emit()

        self.watermark_text_edit.textChanged.connect(emit_document)
        self.font_combo.currentTextChanged.connect(emit_document)
        self.auto_fit_check.toggled.connect(emit_document)

        self.color_picker.color_changed.connect(emit_controls)
        self.blend_combo.currentIndexChanged.connect(emit_controls)
        self.opacity_slider.valueChanged.connect(emit_controls)
        self.brush_size_slider.valueChanged.connect(emit_controls)
        self.angle_slider.valueChanged.connect(emit_controls)
        self.softness_slider.valueChanged.connect(emit_controls)
        self.repeat_text_check.toggled.connect(emit_controls)
        self.repeat_text_check.toggled.connect(self._update_repeat_spacing_enabled)
        self.repeat_spacing_spin.valueChanged.connect(emit_controls)

        self.stroke_list.currentRowChanged.connect(self.layer_selected.emit)
        self.stroke_list.itemPressed.connect(
            lambda item: self.layer_item_pressed.emit(self.stroke_list.row(item))
        )
        self.stroke_list.itemClicked.connect(
            lambda item: self.layer_item_clicked.emit(self.stroke_list.row(item))
        )
        self.delete_selected_btn.clicked.connect(self.delete_selected.emit)
        self.delete_all_btn.clicked.connect(self.delete_all.emit)
        self.ok_button.clicked.connect(self.save_and_close.emit)
        self.exit_button.clicked.connect(self.exit_without_saving.emit)
        self.update_now_button.clicked.connect(self.update_now.emit)
        self._update_repeat_spacing_enabled()

    def _update_repeat_spacing_enabled(self):
        self.repeat_spacing_spin.setEnabled(self.repeat_text_check.isChecked())

    def set_context_label(self, text: str):
        self.context_label.setText(text)

    def _block_control_signals(self, block: bool):
        widgets = (
            self.color_picker,
            self.blend_combo,
            self.opacity_slider,
            self.brush_size_slider,
            self.angle_slider,
            self.softness_slider,
            self.repeat_text_check,
            self.repeat_spacing_spin,
        )
        for widget in widgets:
            widget.blockSignals(block)

    def load_tool_defaults(self, settings: Settings):
        self._block_control_signals(True)
        self.brush_size_slider.setValue(settings.brush_size)
        self.opacity_slider.setValue(settings.opacity)
        self.angle_slider.setValue(settings.angle_offset)
        self.softness_slider.setValue(settings.mask_softness)
        self.repeat_text_check.setChecked(settings.repeat_text)
        self.repeat_spacing_spin.setValue(settings.repeat_spacing)
        self.color_picker.set_selected(settings.text_color)
        blend_index = self.blend_combo.findData(settings.blend_mode)
        if blend_index >= 0:
            self.blend_combo.setCurrentIndex(blend_index)
        self._block_control_signals(False)
        self._update_repeat_spacing_enabled()
        self.set_context_label("Tool defaults")

    def load_stroke_controls(self, stroke: Stroke):
        self._block_control_signals(True)
        self.brush_size_slider.setValue(stroke.brush_size)
        self.opacity_slider.setValue(stroke.opacity)
        self.angle_slider.setValue(stroke.angle_offset)
        self.softness_slider.setValue(stroke.mask_softness)
        self.repeat_text_check.setChecked(stroke.repeat_text)
        self.repeat_spacing_spin.setValue(stroke.repeat_spacing)
        self.color_picker.set_selected(stroke.text_color)
        blend_index = self.blend_combo.findData(stroke.blend_mode)
        if blend_index >= 0:
            self.blend_combo.setCurrentIndex(blend_index)
        self._block_control_signals(False)
        self._update_repeat_spacing_enabled()
        visibility = "visible" if stroke.visible else "hidden"
        self.set_context_label(f"Layer: {stroke.name} · {visibility}")

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
            repeat_text=tool_defaults.repeat_text,
            repeat_spacing=tool_defaults.repeat_spacing,
            blend_mode=tool_defaults.blend_mode,
        )

    def read_stroke_controls(self) -> dict:
        return {
            "brush_size": int(self.brush_size_slider.value()),
            "opacity": int(self.opacity_slider.value()),
            "blend_mode": str(self.blend_combo.currentData()),
            "text_color": self.color_picker.selected_color(),
            "angle_offset": int(self.angle_slider.value()),
            "mask_softness": int(self.softness_slider.value()),
            "repeat_text": bool(self.repeat_text_check.isChecked()),
            "repeat_spacing": int(self.repeat_spacing_spin.value()),
        }

    def read_tool_defaults(self) -> dict:
        return self.read_stroke_controls()

    def set_version_info(self, current_version: str, result: UpdateCheckResult | None = None):
        self.version_label.setText(f"Version {current_version}")
        self.update_now_button.hide()
        if result is None:
            self.update_status_label.setText("Checking for updates...")
            return
        if result.check_failed:
            self.update_status_label.setText("")
            return
        if result.update_available and result.latest_version:
            if can_auto_update() and result.download_url:
                self.update_status_label.setText(
                    f"Version {result.latest_version} is available."
                )
                self.update_now_button.show()
            else:
                self.update_status_label.setText(
                    f'<a href="{result.release_url}">'
                    f"Version {result.latest_version} is available — open release page"
                    f"</a>"
                )
            return
        self.update_status_label.setText("You have the latest version.")

    def set_update_progress(self, percent: int, message: str):
        self.update_now_button.setEnabled(False)
        self.update_progress_label.show()
        self.update_progress_label.setText(message if percent >= 100 else f"{message} ({percent}%)")

    def clear_update_progress(self):
        self.update_now_button.setEnabled(True)
        self.update_progress_label.hide()
        self.update_progress_label.setText("")

    def _make_card(self, title: str):
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 8)
        card_layout.setSpacing(6)
        lbl = QLabel(title)
        lbl.setObjectName("SectionTitle")
        card_layout.addWidget(lbl)
        return card, card_layout

    def _make_field_label(self, prefix: str) -> QLabel:
        label = QLabel(prefix)
        label.setObjectName("FieldLabel")
        label.setProperty("prefix", prefix)
        return label

    def set_field_label_value(self, label: QLabel, value_text: str):
        prefix = label.property("prefix") or ""
        label.setText(f"{prefix}  {value_text}" if prefix else value_text)

    def _add_form_row(self, layout: QVBoxLayout, label_text: str, widget: QWidget, label_width: int = 52):
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        label.setFixedWidth(label_width)
        row.addWidget(label)
        row.addWidget(widget, 1)
        layout.addLayout(row)

    def _add_slider_row(self, layout: QVBoxLayout, label: QLabel, slider: QSlider):
        block = QVBoxLayout()
        block.setSpacing(2)
        block.addWidget(label)
        block.addWidget(slider)
        layout.addLayout(block)

    def _make_slider(self, low: int, high: int, value: int) -> QSlider:
        from PySide6.QtCore import Qt

        s = QSlider(Qt.Horizontal)
        s.setRange(low, high)
        s.setValue(value)
        return s
