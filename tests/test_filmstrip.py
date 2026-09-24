from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest

from brush_watermark.ui.filmstrip import FILMSTRIP_HEIGHT, FilmstripWidget


def make_strip(count: int) -> FilmstripWidget:
    strip = FilmstripWidget()
    pixmaps = []
    for _ in range(count):
        pixmap = QPixmap(98, 66)
        pixmap.fill(Qt.GlobalColor.gray)
        pixmaps.append(pixmap)
    strip.set_thumbnails(pixmaps)
    return strip


def test_items_are_numbered(qapp):
    strip = make_strip(3)
    assert [item._number for item in strip.items()] == [1, 2, 3]
    assert strip.height() == FILMSTRIP_HEIGHT


def test_active_and_dirty_flags(qapp):
    strip = make_strip(3)
    strip.set_active_index(1)
    strip.set_dirty_flags([False, True, False])
    assert [i._active for i in strip.items()] == [False, True, False]
    assert [i._dirty for i in strip.items()] == [False, True, False]


def test_click_emits_index(qapp):
    strip = make_strip(2)
    strip.show()
    seen = []
    strip.imageSelected.connect(seen.append)
    QTest.mouseClick(strip.items()[1], Qt.MouseButton.LeftButton)
    assert seen == [1]


def test_set_thumbnails_replaces_items(qapp):
    strip = make_strip(3)
    strip.set_thumbnails([QPixmap(98, 66)])
    assert len(strip.items()) == 1
