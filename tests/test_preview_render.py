"""Tests for off-thread preview rendering: Document snapshots, the worker, and
MainWindow's live / low-res drag previews."""
import time
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtTest import QTest

from brush_watermark.models import Settings, Stroke
from brush_watermark.services.document import Document, load_documents
from brush_watermark.ui.preview_worker import PreviewJob, PreviewWorker


def _doc(tmp_path: Path, size=(400, 260)) -> Document:
    path = tmp_path / "img.jpg"
    Image.new("RGB", size, (90, 120, 150)).save(path)
    doc = Document(path, Settings(repeat_text=True))
    doc.add_stroke([(20, 130), (200, 60), (380, 130)], 60, 60, "normal", "#ffffff", 0, 1, True, 2)
    return doc


def _wait_until(predicate, timeout_ms: int) -> bool:
    """Process events until predicate() is true (PySide6 lacks QTest.qWaitFor)."""
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate():
        if time.monotonic() > deadline:
            return False
        QTest.qWait(5)
    return True


def _same(a: Image.Image, b: Image.Image) -> bool:
    return a.size == b.size and a.tobytes() == b.tobytes()


# --- Document snapshots ----------------------------------------------------


def test_request_is_unaffected_by_later_edits(tmp_path):
    doc = _doc(tmp_path)
    request = doc.preview_request(400, 260, 1.0)
    (tmp_path / "ref").mkdir()
    expected = _doc(tmp_path / "ref").make_preview_image(400, 260, 1.0)
    doc.move_anchor(0, 1, (200, 220))
    doc.add_erase_to_mask(100, 100)
    assert _same(doc.render_preview(request), expected)


def test_erase_snapshot_follows_mask_changes(tmp_path):
    doc = _doc(tmp_path)
    before = doc.preview_request(400, 260, 1.0)
    assert before.erase_mask is None
    doc.add_erase_to_mask(200, 60)
    after = doc.preview_request(400, 260, 1.0)
    assert after.erase_mask is not None and after.erase_version != before.erase_version
    assert not _same(doc.render_preview(before), doc.render_preview(after))


def test_alternating_sizes_matches_fresh_render(tmp_path):
    doc = _doc(tmp_path)
    doc.add_erase_to_mask(200, 60)
    doc.make_preview_image(400, 260, 1.0)
    doc.make_preview_image(200, 130, 0.5)
    doc.move_anchor(0, 1, (200, 90))
    for size, scale in (((200, 130), 0.5), ((400, 260), 1.0), ((200, 130), 0.5)):
        cached = doc.make_preview_image(*size, scale)
        fresh = Document(doc.image_path, doc.settings)
        fresh.strokes = doc.strokes
        fresh.erase_mask = doc.erase_mask
        fresh._erase_version = doc._erase_version
        assert _same(cached, fresh.make_preview_image(*size, scale))


def test_original_preview_has_no_strokes(tmp_path):
    doc = _doc(tmp_path)
    original = doc.make_original_preview_image(200, 130)
    assert _same(original, doc.original.resize((200, 130), Image.Resampling.LANCZOS).convert("RGBA"))


# --- PreviewWorker -----------------------------------------------------------


def test_worker_renders_the_latest_submitted_job(qapp, tmp_path):
    doc = _doc(tmp_path)
    worker = PreviewWorker()
    results = []
    worker.rendered.connect(lambda job, qimage, ms: results.append((job.generation, qimage.size().toTuple())))
    worker.start()
    try:
        # Submitted back to back: the worker may start on the first, but the
        # middle one is replaced before it is picked up.
        for gen, size in ((1, (400, 260)), (2, (300, 195)), (3, (200, 130))):
            worker.submit(PreviewJob(gen, doc, doc.preview_request(*size, size[0] / 400), None))
        assert _wait_until(lambda: results and results[-1][0] == 3, 5000)
    finally:
        worker.stop()
    assert results[-1] == (3, (200, 130))
    assert [gen for gen, _ in results] in ([1, 3], [3], [1, 2, 3], [2, 3])
    assert len(results) <= 3


# --- MainWindow --------------------------------------------------------------


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    import brush_watermark.ui.main_window as main_window
    from brush_watermark.ui.main_window import MainWindow

    monkeypatch.setattr(main_window, "save_settings", lambda *_a, **_k: None)
    monkeypatch.setattr(MainWindow, "_start_update_check", lambda self: None)
    paths = []
    for i in range(2):
        path = tmp_path / f"img{i}.jpg"
        Image.new("RGB", (320, 200), (90 + i * 40, 120, 150)).save(path)
        paths.append(path)
    docs, _ = load_documents(paths, Settings())
    points = [(20, 100), (160, 40), (300, 100)]
    docs[0].strokes.append(Stroke(name="S", points=list(points), anchors=list(points), brush_size=40, opacity=50))
    win = MainWindow(docs)
    win.resize(1440, 960)
    win.show()
    assert _wait_until(lambda: win._applied_preview_generation > 0 and not win._preview_busy, 5000)
    yield win
    win.close()


def _wait_idle(win) -> None:
    assert _wait_until(lambda: not win._preview_busy and not win.refresh_pending, 5000)


def test_anchor_drag_updates_the_preview_live(window):
    before = window.preview_pixmap.toImage()
    window.doc.selected_stroke_index = 0
    window.selected_anchor_index = 1
    window.anchor_drag_active = True
    start = window._applied_preview_generation
    window._path_move(*window.image_to_canvas_xy(160, 170))
    assert _wait_until(lambda: window._applied_preview_generation > start, 5000)
    assert window.anchor_drag_active  # updated before the mouse was released
    _wait_idle(window)
    assert window.preview_pixmap.toImage() != before


def test_slow_drag_renders_low_res_then_sharp_on_release(window):
    full_size = window.canvas.preview_draw_size
    full_pixmap = (window.preview_pixmap.width(), window.preview_pixmap.height())
    window.doc.selected_stroke_index = 0
    window.selected_anchor_index = 1
    window.anchor_drag_active = True
    window._last_full_render_ms = 1000.0  # pretend this stroke is slow
    window.refresh_preview()
    _wait_idle(window)
    assert window.preview_pixmap.width() < full_pixmap[0]
    assert window.canvas.preview_draw_size == full_size  # still drawn at full size
    window._path_release(0, 0)
    _wait_idle(window)
    assert (window.preview_pixmap.width(), window.preview_pixmap.height()) == full_pixmap


def test_result_for_a_previous_image_is_dropped(window):
    _wait_idle(window)
    stale = PreviewJob(window._preview_generation + 1, window.docs[1], window.docs[1].preview_request(10, 10, 1.0), ((1.0, 1.0), False))
    shown = window.preview_pixmap
    window._apply_preview(stale, shown.copy(0, 0, 10, 10))
    assert window.preview_pixmap is shown


def test_slow_drag_stays_full_res_with_metadata_footer(window):
    # The footer doesn't scale with the image, so a low-res render would lay
    # out taller and make the photo jump when the drag starts.
    window.doc.settings.add_visible_metadata = True
    window.refresh_preview()
    _wait_idle(window)
    layout = (window.canvas.preview_draw_size, window.offset_x, window.offset_y)
    window.doc.selected_stroke_index = 0
    window.selected_anchor_index = 1
    window.anchor_drag_active = True
    window._last_full_render_ms = 1000.0
    window.refresh_preview()
    _wait_idle(window)
    assert (window.canvas.preview_draw_size, window.offset_x, window.offset_y) == layout
