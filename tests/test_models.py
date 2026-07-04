from brush_watermark.config import DEFAULT_SETTINGS, load_settings, save_settings
from brush_watermark.models import Settings, Stroke


class TestSettings:
    def test_from_dict_defaults(self):
        s = Settings.from_dict({})
        assert s.watermark_text == "Erik Simonič"
        assert s.opacity == 22

    def test_round_trip(self):
        original = Settings(
            watermark_text="Test",
            opacity=50,
            brush_size=80,
            blend_mode="difference",
        )
        restored = Settings.from_dict(original.to_dict())
        assert restored.watermark_text == "Test"
        assert restored.opacity == 50
        assert restored.brush_size == 80
        assert restored.blend_mode == "difference"


class TestStroke:
    def test_defaults(self):
        s = Stroke(name="S1", points=[(0, 0), (10, 10)], brush_size=30, opacity=50)
        assert s.visible is True
        assert s.repeat_text is False
        assert s.repeat_spacing == 5


class TestConfigPersistence:
    def test_save_and_load(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_file = config_dir / "settings.json"
        monkeypatch.setattr("brush_watermark.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("brush_watermark.config.CONFIG_FILE", config_file)

        custom = {**DEFAULT_SETTINGS, "opacity": 77, "watermark_text": "Saved"}
        save_settings(custom)
        loaded = load_settings()
        assert loaded["opacity"] == 77
        assert loaded["watermark_text"] == "Saved"

    def test_load_missing_file(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "missing"
        monkeypatch.setattr("brush_watermark.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("brush_watermark.config.CONFIG_FILE", config_dir / "settings.json")
        loaded = load_settings()
        assert loaded == DEFAULT_SETTINGS

    def test_load_corrupt_file(self, tmp_path, monkeypatch):
        config_dir = tmp_path / "config"
        config_file = config_dir / "settings.json"
        config_dir.mkdir()
        config_file.write_text("not json", encoding="utf-8")
        monkeypatch.setattr("brush_watermark.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("brush_watermark.config.CONFIG_FILE", config_file)
        loaded = load_settings()
        assert loaded == DEFAULT_SETTINGS
