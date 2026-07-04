from brush_watermark.models import Settings, Stamp
from brush_watermark.services.document import Document
from brush_watermark.services.stamps import (
    list_stamps,
    reload_stamp_catalog,
    render_stamp_rgba,
    stamp_bounds,
    stamp_height_px,
    stamp_hit_test,
    stamp_pixel_size,
    normalize_stamp_size_percent,
)


class TestStampAssets:
    def test_bundled_stamps_exist(self):
        names = list_stamps()
        assert "sample-star.svg" in names
        assert "sample-badge.svg" in names
        assert "sample-mark.png" in names

    def test_reload_stamp_catalog(self):
        first = reload_stamp_catalog()
        second = reload_stamp_catalog()
        assert first == second
        assert "sample-star.svg" in second

    def test_render_png_stamp(self):
        image = render_stamp_rgba("sample-mark.png", 48, None)
        assert image.mode == "RGBA"
        assert image.getbbox() is not None
        assert image.height == 48

    def test_render_stamp_rgba(self):
        image = render_stamp_rgba("sample-star.svg", 80, None)
        assert image.mode == "RGBA"
        assert image.getbbox() is not None
        assert image.height == 80

    def test_render_stamp_with_tint(self):
        native = render_stamp_rgba("sample-star.svg", 60, None)
        tinted = render_stamp_rgba("sample-star.svg", 60, "#ff0000")
        assert native.getbbox() == tinted.getbbox()
        assert native.getpixel((30, 30)) != tinted.getpixel((30, 30))

    def test_stamp_height_from_percent(self):
        assert stamp_height_px(10, 2000) == 200
        assert stamp_height_px(100, 500) == 500

    def test_legacy_stamp_size_migration(self):
        assert normalize_stamp_size_percent(438, legacy_pixels=True) == 44
        assert normalize_stamp_size_percent(150, legacy_pixels=True) == 150
        assert normalize_stamp_size_percent(15, legacy_pixels=True) == 15

    def test_stamp_bounds_bottom_left_anchor(self):
        image_height = 1000
        height_px = stamp_height_px(100, image_height)
        width, height = stamp_pixel_size("sample-star.svg", height_px)
        left, top, right, bottom = stamp_bounds(
            "sample-star.svg", 20, 200, 100, image_height
        )
        assert left == 20
        assert bottom == 200
        assert top == 200 - height
        assert right == 20 + width


class TestStampDocument:
    def test_add_and_hit_test(self, tmp_path, monkeypatch):
        from PIL import Image

        image_path = tmp_path / "photo.jpg"
        Image.new("RGB", (400, 300), (120, 120, 120)).save(image_path, quality=90)

        doc = Document(image_path, Settings())
        stamp = doc.add_stamp("sample-star.svg", 50, 180, 30, 40, "soft_light", None)
        assert stamp.name == "Stamp 1"
        assert doc.find_stamp_at_point(50, 180) == 0
        assert doc.find_stamp_at_point(5, 5) == -1

    def test_move_selected_stamp(self, tmp_path):
        from PIL import Image

        image_path = tmp_path / "photo.jpg"
        Image.new("RGB", (200, 200), (100, 100, 100)).save(image_path, quality=90)
        doc = Document(image_path, Settings())
        doc.add_stamp("sample-star.svg", 10, 100, 25, 30, "normal", None)
        doc.select_stamp(0)
        doc.move_selected_stamp(5, -3)
        assert doc.stamps[0].x == 15
        assert doc.stamps[0].y == 97

    def test_preview_renders_stamp_at_scaled_size(self, tmp_path):
        from PIL import Image
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        assert app is not None

        image_path = tmp_path / "photo.jpg"
        Image.new("RGB", (4000, 3000), (100, 150, 200)).save(image_path, quality=90)
        doc = Document(image_path, Settings())
        doc.add_stamp("sample-badge.svg", 200, 400, 15, 100, "normal", None)

        scale = 0.25
        preview = doc.make_preview_image(1000, 750, scale)
        bg = (100, 150, 200, 255)
        changed = [
            (x, y)
            for y in range(preview.height)
            for x in range(preview.width)
            if preview.getpixel((x, y)) != bg
        ]
        assert len(changed) > 500
        xs = [x for x, _ in changed]
        ys = [y for _, y in changed]
        width = max(xs) - min(xs) + 1
        height = max(ys) - min(ys) + 1
        assert width > 80
        assert height > 30


class TestStampHitTest:
    def test_stamp_hit_test_helper(self):
        stamp = Stamp(
            name="S1",
            svg_name="sample-star.svg",
            x=30,
            y=120,
            size=60,
            opacity=50,
        )
        assert stamp_hit_test(stamp, 30, 120, 200)
        assert not stamp_hit_test(stamp, 0, 0, 200)
