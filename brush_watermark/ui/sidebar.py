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
    QVBoxLayout,
    QWidget,
)

from brush_watermark.models import Settings
from brush_watermark.rendering.fonts import font_candidates


class SidebarPanel(QWidget):
    settings_changed = Signal()
    layer_selected = Signal(int)
    layer_item_pressed = Signal(int)
    layer_item_clicked = Signal(int)
    delete_selected = Signal()
    delete_all = Signal()
    selected_stroke_changed = Signal()
    save_and_close = Signal()
    exit_without_saving = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self._build_ui(settings)
        self._connect_signals()

    def _build_ui(self, settings: Settings):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        defaults_card, defaults_layout = self._make_card("New stroke defaults")
        layout.addWidget(defaults_card)

        self.watermark_text_edit = QLineEdit(settings.watermark_text)
        self.font_combo = QComboBox()
        self.font_combo.addItems(list(font_candidates().keys()))
        self.font_combo.setCurrentText(settings.font_name)
        self.color_combo = QComboBox()
        self.color_combo.addItems(["white", "black"])
        self.color_combo.setCurrentText(settings.text_color)

        self.opacity_value_label = self._make_field_label("Opacity")
        self.opacity_slider = self._make_slider(1, 100, settings.opacity)
        self.brush_value_label = self._make_field_label("Brush")
        self.brush_size_slider = self._make_slider(5, 600, settings.brush_size)
        self.font_size_value_label = QLabel()
        self.font_size_value_label.setObjectName("HintLabel")
        self.angle_value_label = self._make_field_label("Angle")
        self.angle_slider = self._make_slider(-20, 20, settings.angle_offset)
        self.softness_value_label = self._make_field_label("Softness")
        self.softness_slider = self._make_slider(0, 20, settings.mask_softness)
        self.auto_fit_check = QCheckBox("Auto fit text to stroke")
        self.auto_fit_check.setChecked(settings.auto_fit_text)

        self._add_form_row(defaults_layout, "Text", self.watermark_text_edit)
        self._add_form_row(defaults_layout, "Font", self.font_combo)
        self._add_form_row(defaults_layout, "Color", self.color_combo)
        self._add_slider_row(defaults_layout, self.opacity_value_label, self.opacity_slider)
        self._add_slider_row(defaults_layout, self.brush_value_label, self.brush_size_slider)
        defaults_layout.addWidget(self.font_size_value_label)
        self._add_slider_row(defaults_layout, self.angle_value_label, self.angle_slider)
        self._add_slider_row(defaults_layout, self.softness_value_label, self.softness_slider)
        defaults_layout.addWidget(self.auto_fit_check)

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

        selected_card, selected_layout = self._make_card("Selected layer")
        layout.addWidget(selected_card)
        self.selected_info_label = QLabel("No stroke selected")
        self.selected_info_label.setObjectName("HintLabel")
        self.sel_brush_value_label = self._make_field_label("Brush")
        self.sel_brush_slider = self._make_slider(5, 600, 120)
        self.sel_font_value_label = QLabel()
        self.sel_font_value_label.setObjectName("HintLabel")
        self.sel_opacity_value_label = self._make_field_label("Opacity")
        self.sel_opacity_slider = self._make_slider(1, 100, 22)
        selected_layout.addWidget(self.selected_info_label)
        self._add_slider_row(selected_layout, self.sel_brush_value_label, self.sel_brush_slider)
        selected_layout.addWidget(self.sel_font_value_label)
        self._add_slider_row(selected_layout, self.sel_opacity_value_label, self.sel_opacity_slider)

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
            "Erase: right mouse · Wheel: opacity · Alt+wheel: brush/font size · "
            "Selected layer shows a faint guide."
        )
        help_text.setWordWrap(True)
        help_text.setObjectName("HintLabel")
        help_layout.addWidget(help_text)
        layout.addStretch(1)

    def _connect_signals(self):
        self.watermark_text_edit.textChanged.connect(self.settings_changed.emit)
        self.font_combo.currentTextChanged.connect(self.settings_changed.emit)
        self.color_combo.currentTextChanged.connect(self.settings_changed.emit)
        self.opacity_slider.valueChanged.connect(self.settings_changed.emit)
        self.brush_size_slider.valueChanged.connect(self.settings_changed.emit)
        self.angle_slider.valueChanged.connect(self.settings_changed.emit)
        self.softness_slider.valueChanged.connect(self.settings_changed.emit)
        self.auto_fit_check.toggled.connect(self.settings_changed.emit)

        self.stroke_list.currentRowChanged.connect(self.layer_selected.emit)
        self.stroke_list.itemPressed.connect(
            lambda item: self.layer_item_pressed.emit(self.stroke_list.row(item))
        )
        self.stroke_list.itemClicked.connect(
            lambda item: self.layer_item_clicked.emit(self.stroke_list.row(item))
        )
        self.delete_selected_btn.clicked.connect(self.delete_selected.emit)
        self.delete_all_btn.clicked.connect(self.delete_all.emit)
        self.sel_brush_slider.valueChanged.connect(self.selected_stroke_changed.emit)
        self.sel_opacity_slider.valueChanged.connect(self.selected_stroke_changed.emit)
        self.ok_button.clicked.connect(self.save_and_close.emit)
        self.exit_button.clicked.connect(self.exit_without_saving.emit)

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

    def read_settings(self) -> Settings:
        return Settings(
            watermark_text=self.watermark_text_edit.text(),
            opacity=int(self.opacity_slider.value()),
            font_name=self.font_combo.currentText(),
            brush_size=int(self.brush_size_slider.value()),
            angle_offset=int(self.angle_slider.value()),
            mask_softness=int(self.softness_slider.value()),
            text_color=self.color_combo.currentText(),
            auto_fit_text=bool(self.auto_fit_check.isChecked()),
        )
