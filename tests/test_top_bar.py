from PySide6.QtWidgets import QMenu, QPushButton, QWidget

from brush_watermark.ui.top_bar import TopBar


def test_file_info_toggles_optional_parts(qapp):
    bar = TopBar()
    bar.set_file_info("a.jpg", None, 0, 1)
    assert bar.file_name_label.text() == "a.jpg"
    assert bar.serial_chip.isHidden() and bar.index_badge.isHidden()
    bar.set_file_info("b.jpg", "6022905", 1, 6)
    assert bar.serial_chip.text() == "#6022905" and not bar.serial_chip.isHidden()
    assert bar.index_badge.text() == "2 / 6" and not bar.index_badge.isHidden()


def test_unsaved_indicator(qapp):
    bar = TopBar()
    assert bar.unsaved_indicator.isHidden()
    bar.set_unsaved(True)
    assert not bar.unsaved_indicator.isHidden()


def test_preview_toggle_defaults_to_watermarked_and_emits(qapp):
    bar = TopBar()
    seen = []
    bar.preview_changed.connect(seen.append)
    assert bar.show_original() is False
    bar.preview_toggle.setCurrentIndex(0)
    assert bar.show_original() is True and seen == [True]


def test_save_buttons_and_actions_emit(qapp):
    bar = TopBar()
    seen = []
    bar.save_and_close.connect(lambda: seen.append("save"))
    bar.save_copy_and_close.connect(lambda: seen.append("copy"))
    bar.save_all_and_close.connect(lambda: seen.append("all"))
    bar.exit_without_saving.connect(lambda: seen.append("exit"))
    bar.save_split.main.click()
    bar.save_copy_button.click()
    bar.exit_button.click()
    bar.save_all_action.trigger()
    bar.save_copy_action.trigger()
    bar.save_close_action.trigger()
    assert seen == ["save", "copy", "exit", "all", "copy", "save"]


def test_long_file_name_elides_and_keeps_minimum_width_within_window(qapp):
    container = QWidget()
    bar = TopBar(container)
    bar.setGeometry(0, 0, 1180, TopBar.HEIGHT)
    container.resize(1180, TopBar.HEIGHT)
    container.show()
    assert bar.width() == 1180
    long_name = "x" * 80 + ".jpg"
    bar.set_file_info(long_name, "6022905", 1, 6)
    bar.set_unsaved(True)
    bar.resize(1180, TopBar.HEIGHT)
    from PySide6.QtWidgets import QApplication

    QApplication.instance().processEvents()
    assert bar.minimumSizeHint().width() <= 1180
    assert bar.file_name_label.toolTip() == long_name
    assert "…" in bar.file_name_label.text()


def test_multi_document_mode_shows_edited_count(qapp):
    bar = TopBar()
    assert not bar.save_all_action.isVisible()
    bar.set_multi_document_mode(True, 3)
    assert bar.save_all_action.isVisible()
    assert bar.save_all_action.text() == "Save all && close (3 edited)"


def test_add_menu_adds_a_menu_button(qapp):
    bar = TopBar()
    menu = bar.add_menu("&File")
    assert isinstance(menu, QMenu)
    buttons = [b for b in bar.findChildren(QPushButton) if b.objectName() == "MenuButton"]
    assert [b.text() for b in buttons] == ["&File"] and buttons[0].menu() is menu


def test_copy_serial_puts_serial_on_clipboard(qapp):
    from PySide6.QtWidgets import QApplication

    bar = TopBar()
    bar.set_file_info("b.jpg", "6022905", 0, 1)
    assert not bar.serial_box.isHidden()
    bar.copy_serial_button.click()
    assert QApplication.clipboard().text() == "6022905"
    assert bar.copy_serial_button.toolTip() == "Copied"


def test_serial_box_hidden_without_serial(qapp):
    bar = TopBar()
    bar.set_file_info("a.jpg", None, 0, 1)
    assert bar.serial_box.isHidden()


def test_save_menu_shows_ctrl_s(qapp):
    assert TopBar().save_close_action.text().endswith("	Ctrl+S")
