from PySide6.QtWidgets import QWidget

from brush_watermark.services.update_check import UpdateCheckResult
from brush_watermark.ui.status_footer import StatusFooter


def result(**kwargs) -> UpdateCheckResult:
    base = dict(current_version="1.15.0", latest_version="1.15.0", update_available=False, release_url="https://example.invalid/r")
    base.update(kwargs)
    return UpdateCheckResult(**base)


def test_checking_state(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0")
    assert footer.version_label.text() == "v1.15.0 · Checking for updates…"


def test_up_to_date(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0", result())
    assert footer.version_label.text() == "v1.15.0 · Up to date"
    assert footer.update_now_button.isHidden() and footer.update_link.isHidden()


def test_update_with_download_shows_button_that_emits(qapp):
    footer = StatusFooter()
    footer.set_version_info(
        "1.15.0", result(latest_version="1.16.0", update_available=True, download_url="https://example.invalid/z")
    )
    assert not footer.update_now_button.isHidden()
    assert footer.update_now_button.text() == "Update to v1.16.0"
    seen = []
    footer.update_now.connect(lambda: seen.append(True))
    footer.update_now_button.click()
    assert seen == [True]


def test_update_without_download_shows_link(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0", result(latest_version="1.16.0", update_available=True))
    assert not footer.update_link.isHidden() and "https://example.invalid/r" in footer.update_link.text()


def test_failed_check_shows_version_only(qapp):
    footer = StatusFooter()
    footer.set_version_info("1.15.0", result(check_failed=True))
    assert footer.version_label.text() == "v1.15.0"


def test_update_widgets_fit_at_minimum_window_width(qapp):
    container = QWidget()
    footer = StatusFooter(container)
    footer.setGeometry(0, 0, 1180, StatusFooter.HEIGHT)
    container.resize(1180, StatusFooter.HEIGHT)
    container.show()
    assert footer.width() == 1180
    footer.set_version_info(
        "1.15.0", result(latest_version="1.16.0", update_available=True, download_url="https://example.invalid/z")
    )
    footer.set_update_progress(45, "Downloading update…")
    qapp.processEvents()
    assert footer.update_now_button.width() >= footer.update_now_button.minimumSizeHint().width()
    assert footer.progress_label.width() >= footer.progress_label.sizeHint().width()


def test_progress(qapp):
    footer = StatusFooter()
    footer.set_update_progress(40, "Downloading")
    assert footer.progress_label.text() == "Downloading (40%)" and not footer.update_now_button.isEnabled()
    footer.clear_update_progress()
    assert footer.progress_label.isHidden() and footer.update_now_button.isEnabled()
