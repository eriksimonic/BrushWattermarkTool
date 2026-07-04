from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from brush_watermark.models import Settings, Stamp, Stroke, ToolMode
from brush_watermark.rendering.blend import BLEND_MODE_CHOICES
from brush_watermark.rendering.fonts import font_candidates
from brush_watermark.services.stamps import list_stamp_svgs
from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.color_picker import ColorSwatchPicker
from brush_watermark.ui.lightroom_controls import BoxCheckBox, SectionHeader, SliderRow


class SidebarPanel(QWidget):
    document_settings_changed = Signal()
    stroke_controls_changed = Signal()
    tool_mode_changed = Signal(str)
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
        self.setFixedWidth(340)
        self._build_ui(settings)
        self._connect_signals()
        self.load_tool_defaults(settings)

    def _build_ui(self, settings: Settings):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(2)

        layout.addWidget(SectionHeader("Watermark"))
        watermark_layout = QVBoxLayout()
        watermark_layout.setSpacing(4)
        layout.addLayout(watermark_layout)

        tool_row = QHBoxLayout()
        tool_row.setSpacing(6)
        self.paint_tool_btn = QPushButton("Paint")
        self.stamp_tool_btn = QPushButton("Stamp")
        self.paint_tool_btn.setCheckable(True)
        self.stamp_tool_btn.setCheckable(True)
        self.paint_tool_btn.setChecked(settings.tool_mode == "paint")
        self.stamp_tool_btn.setChecked(settings.tool_mode == "stamp")
        tool_row.addWidget(self.paint_tool_btn)
        tool_row.addWidget(self.stamp_tool_btn)
        watermark_layout.addLayout(tool_row)

        self.watermark_text_edit = QLineEdit(settings.watermark_text)
        self.font_combo = QComboBox()
        self.font_combo.addItems(list(font_candidates().keys()))
        self.font_combo.setCurrentText(settings.font_name)
        self.auto_fit_check = BoxCheckBox("Auto fit text to stroke")
        self.auto_fit_check.setChecked(settings.auto_fit_text)

        self.stamp_combo = QComboBox()
        self.stamp_combo.setToolTip("SVG stamp to place on the canvas")
        self.stamp_empty_label = QLabel("Add .svg files to assets/stamps/")
        self.stamp_empty_label.setObjectName("HintLabel")
        self.stamp_empty_label.setWordWrap(True)

        self._add_form_row(watermark_layout, "Text", self.watermark_text_edit, row_attr="text_form_row")
        self._add_form_row(watermark_layout, "Font", self.font_combo, row_attr="font_form_row")
        watermark_layout.addWidget(self.auto_fit_check)
        self._add_form_row(watermark_layout, "Stamp", self.stamp_combo, row_attr="stamp_form_row")
        watermark_layout.addWidget(self.stamp_empty_label)

        self.use_svg_colors_check = BoxCheckBox("Use SVG colors")
        self.use_svg_colors_check.setChecked(settings.use_svg_colors)
        watermark_layout.addWidget(self.use_svg_colors_check)

        self.brush_section = SectionHeader("Brush")
        layout.addWidget(self.brush_section)
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(3)
        layout.addLayout(controls_layout)

        self.color_picker = ColorSwatchPicker()
        self.color_picker.set_swatches(self._swatch_colors, settings.text_color)
        controls_layout.addWidget(self.color_picker)

        self.blend_combo = QComboBox()
        for mode_key, mode_label in BLEND_MODE_CHOICES:
            self.blend_combo.addItem(mode_label, mode_key)

        self.opacity_row = SliderRow("Strength", 1, 100, settings.opacity)
        self.brush_row = SliderRow("Brush size", 5, 600, settings.brush_size)
        self.font_size_value_label = QLabel()
        self.font_size_value_label.setObjectName("HintLabel")
        self.softness_row = SliderRow("Softness", 0, 20, settings.mask_softness)
        self.repeat_text_check = BoxCheckBox("Repeat text along stroke")
        self.repeat_text_check.setChecked(settings.repeat_text)
        self.repeat_spacing_spin = QSpinBox()
        self.repeat_spacing_spin.setRange(0, 50)
        self.repeat_spacing_spin.setValue(settings.repeat_spacing)
        self.repeat_spacing_spin.setToolTip("Space between repeats, in character widths")
        self.repeat_spacing_spin.setFixedWidth(56)
        self.repeat_row = QWidget()
        repeat_row = QHBoxLayout(self.repeat_row)
        repeat_row.setContentsMargins(0, 0, 0, 0)
        repeat_row.setSpacing(8)
        repeat_row.addWidget(self.repeat_text_check, 1)
        repeat_row.addWidget(QLabel("gap"))
        repeat_row.addWidget(self.repeat_spacing_spin)

        self._add_form_row(controls_layout, "Blend", self.blend_combo)
        controls_layout.addWidget(self.opacity_row)
        controls_layout.addWidget(self.brush_row)
        controls_layout.addWidget(self.font_size_value_label)
        controls_layout.addWidget(self.softness_row)
        controls_layout.addWidget(self.repeat_row)

        layout.addWidget(SectionHeader("Layers"))
        layers_layout = QVBoxLayout()
        layers_layout.setSpacing(4)
        layout.addLayout(layers_layout)

        self.stroke_list = QListWidget()
        self.stroke_list.setFixedHeight(110)
        self.stroke_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layers_layout.addWidget(self.stroke_list)

        layer_actions = QHBoxLayout()
        layer_actions.setSpacing(6)
        self.delete_selected_btn = QPushButton("Delete")
        self.delete_all_btn = QPushButton("Clear all")
        layer_actions.addWidget(self.delete_selected_btn)
        layer_actions.addWidget(self.delete_all_btn)
        layers_layout.addLayout(layer_actions)

        actions = QVBoxLayout()
        actions.setSpacing(4)
        self.reveal_in_explorer_check = BoxCheckBox("Show in Explorer after save")
        self.reveal_in_explorer_check.setChecked(True)
        actions.addWidget(self.reveal_in_explorer_check)
        self.ok_button = QPushButton("Save and close")
        self.ok_button.setObjectName("PrimaryButton")
        self.exit_button = QPushButton("Exit without saving")
        actions.addWidget(self.ok_button)
        actions.addWidget(self.exit_button)
        layout.addLayout(actions)

        layout.addWidget(SectionHeader("Help"))
        help_layout = QVBoxLayout()
        help_layout.setSpacing(2)
        layout.addLayout(help_layout)
        help_text = QLabel(
            "Paint: left drag · Stamp: left click to place · Select: click layer · "
            "Move stamp: drag or arrow keys (Shift = 10 px) · Erase: right mouse · "
            "Wheel: strength · Alt+wheel: brush/stamp size · "
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
        self.refresh_stamp_list(settings.stamp_name)
        self.set_tool_mode(settings.tool_mode)

    def refresh_stamp_list(self, preferred: str = ""):
        names = list_stamp_svgs()
        self.stamp_combo.blockSignals(True)
        self.stamp_combo.clear()
        self.stamp_combo.addItems(names)
        if preferred in names:
            self.stamp_combo.setCurrentText(preferred)
        elif names:
            self.stamp_combo.setCurrentIndex(0)
        self.stamp_combo.blockSignals(False)
        has_stamps = bool(names)
        self.stamp_combo.setEnabled(has_stamps)
        self.stamp_empty_label.setVisible(not has_stamps)
        self.stamp_tool_btn.setEnabled(has_stamps)

    def set_tool_mode(self, mode: ToolMode):
        paint = mode == "paint"
        stamp = mode == "stamp"
        self.paint_tool_btn.blockSignals(True)
        self.stamp_tool_btn.blockSignals(True)
        self.paint_tool_btn.setChecked(paint)
        self.stamp_tool_btn.setChecked(stamp)
        self.paint_tool_btn.blockSignals(False)
        self.stamp_tool_btn.blockSignals(False)
        self._apply_tool_context(mode, stamp_selected=False)

    def _apply_tool_context(self, mode: ToolMode, *, stamp_selected: bool):
        show_text_controls = mode == "paint" and not stamp_selected
        show_stamp_controls = mode == "stamp" or stamp_selected

        self.text_form_row.setVisible(show_text_controls)
        self.font_form_row.setVisible(show_text_controls)
        self.auto_fit_check.setVisible(show_text_controls)
        self.stamp_form_row.setVisible(show_stamp_controls)
        self.stamp_empty_label.setVisible(show_stamp_controls and self.stamp_combo.count() == 0)
        self.use_svg_colors_check.setVisible(show_stamp_controls)

        show_stroke_only = show_text_controls
        self.softness_row.setVisible(show_stroke_only)
        self.repeat_row.setVisible(show_stroke_only)
        self.font_size_value_label.setVisible(show_stroke_only)

        if show_stamp_controls:
            self.brush_row.set_label("Stamp size")
        else:
            self.brush_row.set_label("Brush size")
        self._refresh_layout()

    def set_controls_context(self, *, tool_mode: ToolMode, stamp_selected: bool):
        self._apply_tool_context(tool_mode, stamp_selected=stamp_selected)

    def _refresh_layout(self):
        self.adjustSize()
        parent = self.parentWidget()
        while parent is not None:
            parent.updateGeometry()
            if isinstance(parent, QScrollArea):
                break
            parent = parent.parentWidget()

    def _connect_signals(self):
        emit_document = lambda *_: self.document_settings_changed.emit()
        emit_controls = lambda *_: self.stroke_controls_changed.emit()

        self.watermark_text_edit.textChanged.connect(emit_document)
        self.font_combo.currentTextChanged.connect(emit_document)
        self.auto_fit_check.toggled.connect(emit_document)
        self.stamp_combo.currentTextChanged.connect(emit_document)
        self.use_svg_colors_check.toggled.connect(emit_controls)
        self.paint_tool_btn.clicked.connect(self._on_paint_tool_clicked)
        self.stamp_tool_btn.clicked.connect(self._on_stamp_tool_clicked)

        self.color_picker.color_changed.connect(emit_controls)
        self.blend_combo.currentIndexChanged.connect(emit_controls)
        self.opacity_row.slider.valueChanged.connect(emit_controls)
        self.brush_row.slider.valueChanged.connect(emit_controls)
        self.softness_row.slider.valueChanged.connect(emit_controls)
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

    def _on_paint_tool_clicked(self):
        if not self.paint_tool_btn.isChecked():
            self.paint_tool_btn.setChecked(True)
            return
        self.stamp_tool_btn.setChecked(False)
        self.tool_mode_changed.emit("paint")

    def _on_stamp_tool_clicked(self):
        if not self.stamp_tool_btn.isChecked():
            self.stamp_tool_btn.setChecked(True)
            return
        self.paint_tool_btn.setChecked(False)
        self.tool_mode_changed.emit("stamp")

    def _update_repeat_spacing_enabled(self):
        self.repeat_spacing_spin.setEnabled(self.repeat_text_check.isChecked())

    def set_brush_context(self, *, layer_name: str | None = None, visible: bool = True):
        if layer_name is None:
            self.brush_section.set_title("Brush")
            return
        title = f"Layer · {layer_name}"
        if not visible:
            title += " · hidden"
        self.brush_section.set_title(title)

    def _block_control_signals(self, block: bool):
        widgets = (
            self.color_picker,
            self.blend_combo,
            self.opacity_row.slider,
            self.brush_row.slider,
            self.softness_row.slider,
            self.repeat_text_check,
            self.repeat_spacing_spin,
            self.stamp_combo,
            self.use_svg_colors_check,
        )
        for widget in widgets:
            widget.blockSignals(block)

    def load_tool_defaults(self, settings: Settings):
        self._block_control_signals(True)
        self.brush_row.slider.setValue(settings.brush_size if settings.tool_mode == "paint" else settings.stamp_size)
        self.opacity_row.slider.setValue(settings.opacity)
        self.softness_row.slider.setValue(settings.mask_softness)
        self.repeat_text_check.setChecked(settings.repeat_text)
        self.repeat_spacing_spin.setValue(settings.repeat_spacing)
        self.color_picker.set_selected(settings.text_color)
        self.use_svg_colors_check.setChecked(settings.use_svg_colors)
        self.refresh_stamp_list(settings.stamp_name)
        blend_index = self.blend_combo.findData(settings.blend_mode)
        if blend_index >= 0:
            self.blend_combo.setCurrentIndex(blend_index)
        self._block_control_signals(False)
        self._update_repeat_spacing_enabled()
        self.set_brush_context()
        self.set_tool_mode(settings.tool_mode)
        self.set_controls_context(tool_mode=settings.tool_mode, stamp_selected=False)

    def load_stroke_controls(self, stroke: Stroke):
        self._block_control_signals(True)
        self.brush_row.slider.setValue(stroke.brush_size)
        self.opacity_row.slider.setValue(stroke.opacity)
        self.softness_row.slider.setValue(stroke.mask_softness)
        self.repeat_text_check.setChecked(stroke.repeat_text)
        self.repeat_spacing_spin.setValue(stroke.repeat_spacing)
        self.color_picker.set_selected(stroke.text_color)
        blend_index = self.blend_combo.findData(stroke.blend_mode)
        if blend_index >= 0:
            self.blend_combo.setCurrentIndex(blend_index)
        self._block_control_signals(False)
        self._update_repeat_spacing_enabled()
        self.set_brush_context(layer_name=stroke.name, visible=stroke.visible)
        self.set_controls_context(tool_mode=self.current_tool_mode(), stamp_selected=False)

    def load_stamp_controls(self, stamp: Stamp):
        self._block_control_signals(True)
        self.brush_row.slider.setValue(stamp.size)
        self.opacity_row.slider.setValue(stamp.opacity)
        self.color_picker.set_selected(stamp.tint_color or self.color_picker.selected_color())
        self.use_svg_colors_check.setChecked(stamp.tint_color is None)
        self.refresh_stamp_list(stamp.svg_name)
        blend_index = self.blend_combo.findData(stamp.blend_mode)
        if blend_index >= 0:
            self.blend_combo.setCurrentIndex(blend_index)
        self._block_control_signals(False)
        self.set_brush_context(layer_name=stamp.name, visible=stamp.visible)
        self.set_controls_context(tool_mode=self.current_tool_mode(), stamp_selected=True)

    def current_tool_mode(self) -> ToolMode:
        return "stamp" if self.stamp_tool_btn.isChecked() else "paint"

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
            tool_mode=self.current_tool_mode(),
            stamp_name=self.stamp_combo.currentText(),
            stamp_size=tool_defaults.stamp_size,
            use_svg_colors=bool(self.use_svg_colors_check.isChecked()),
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

    def read_stamp_controls(self) -> dict:
        use_native = bool(self.use_svg_colors_check.isChecked())
        return {
            "size": int(self.brush_row.slider.value()),
            "opacity": int(self.opacity_row.slider.value()),
            "blend_mode": str(self.blend_combo.currentData()),
            "tint_color": None if use_native else self.color_picker.selected_color(),
            "svg_name": self.stamp_combo.currentText(),
        }

    def read_tool_defaults(self) -> dict:
        if self.current_tool_mode() == "stamp":
            stamp = self.read_stamp_controls()
            return {
                "brush_size": stamp["size"],
                "opacity": stamp["opacity"],
                "blend_mode": stamp["blend_mode"],
                "text_color": self.color_picker.selected_color(),
                "angle_offset": 0,
                "mask_softness": 1,
                "repeat_text": False,
                "repeat_spacing": 5,
                "stamp_size": stamp["size"],
                "stamp_name": stamp["svg_name"],
                "use_svg_colors": self.use_svg_colors_check.isChecked(),
            }
        stroke = self.read_stroke_controls()
        stroke["stamp_size"] = int(self.brush_row.slider.value())
        stroke["stamp_name"] = self.stamp_combo.currentText()
        stroke["use_svg_colors"] = bool(self.use_svg_colors_check.isChecked())
        return stroke

    def set_version_info(self, current_version: str, result: UpdateCheckResult | None = None):
        self.version_label.setText(f"Version {current_version}")
        self.update_now_button.hide()
        self._refresh_layout()
        if result is None:
            self.update_status_label.setText("Checking for updates...")
            self._refresh_layout()
            return
        if result.check_failed:
            self.update_status_label.setText("")
            self._refresh_layout()
            return
        if result.update_available and result.latest_version:
            if result.download_url:
                self.update_status_label.setText(
                    f"Version {result.latest_version} is available."
                )
                self.update_now_button.show()
            else:
                self.update_status_label.setTextFormat(Qt.TextFormat.RichText)
                self.update_status_label.setText(
                    f'<a href="{result.release_url}">'
                    f"Version {result.latest_version} is available — open release page"
                    f"</a>"
                )
            self._refresh_layout()
            return
        self.update_status_label.setText("You have the latest version.")
        self._refresh_layout()

    def set_update_progress(self, percent: int, message: str):
        self.update_now_button.setEnabled(False)
        self.update_progress_label.show()
        self.update_progress_label.setText(message if percent >= 100 else f"{message} ({percent}%)")
        self._refresh_layout()

    def clear_update_progress(self):
        self.update_now_button.setEnabled(True)
        self.update_progress_label.hide()
        self.update_progress_label.setText("")
        self._refresh_layout()

    def set_slider_value(self, row: SliderRow, value_text: str):
        row.set_value_text(value_text)

    def _add_form_row(
        self,
        layout: QVBoxLayout,
        label_text: str,
        widget: QWidget,
        label_width: int = 52,
        row_attr: str | None = None,
    ):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        label.setFixedWidth(label_width)
        row.addWidget(label)
        row.addWidget(widget, 1)
        layout.addWidget(container)
        if row_attr:
            setattr(self, row_attr, container)
