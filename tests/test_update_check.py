import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from brush_watermark.services.auto_update import (
    build_updater_script,
    can_auto_update,
    extract_update,
    format_exe_args,
    format_ps_argument_list,
    install_directory,
)
from brush_watermark.services.update_check import (
    UpdateCheckResult,
    check_for_update,
    fetch_latest_release,
    is_newer_version,
    parse_release_payload,
    parse_version,
)


class TestParseVersion:
    def test_parses_semver(self):
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_parses_tag_prefix(self):
        assert parse_version("v2.0.0") == (2, 0, 0)


class TestIsNewerVersion:
    def test_patch_bump(self):
        assert is_newer_version("1.0.1", "1.0.0")

    def test_same_version(self):
        assert not is_newer_version("1.0.0", "1.0.0")

    def test_older_remote(self):
        assert not is_newer_version("1.0.0", "1.1.0")


class TestParseReleasePayload:
    def test_reads_version_and_asset(self):
        payload = {
            "tag_name": "v2.3.4",
            "assets": [
                {"name": "BrushWatermark.zip", "browser_download_url": "https://example.com/app.zip"},
                {"name": "notes.txt", "browser_download_url": "https://example.com/notes.txt"},
            ],
        }
        assert parse_release_payload(payload) == ("2.3.4", "https://example.com/app.zip")

    def test_missing_asset_returns_none_url(self):
        payload = {"tag_name": "v1.0.0", "assets": []}
        assert parse_release_payload(payload) == ("1.0.0", None)


class TestFetchLatestRelease:
    def test_parses_github_response(self):
        payload = {
            "tag_name": "v9.0.0",
            "assets": [
                {"name": "BrushWatermark.zip", "browser_download_url": "https://example.com/app.zip"},
            ],
        }
        with patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode(
                "utf-8"
            )
            assert fetch_latest_release() == ("9.0.0", "https://example.com/app.zip")


class TestCheckForUpdate:
    def test_update_available(self):
        with patch(
            "brush_watermark.services.update_check.fetch_latest_release",
            return_value=("9.0.0", "https://example.com/app.zip"),
        ):
            result = check_for_update()
        assert result.update_available is True
        assert result.latest_version == "9.0.0"
        assert result.download_url == "https://example.com/app.zip"
        assert result.check_failed is False

    def test_up_to_date(self):
        with patch(
            "brush_watermark.services.update_check.fetch_latest_release",
            return_value=("1.0.0", "https://example.com/app.zip"),
        ):
            result = check_for_update()
        assert result.update_available is False
        assert isinstance(result, UpdateCheckResult)

    def test_network_failure(self):
        with patch(
            "brush_watermark.services.update_check.fetch_latest_release",
            side_effect=OSError("offline"),
        ), patch(
            "brush_watermark.services.update_check.fetch_remote_version",
            side_effect=OSError("offline"),
        ):
            result = check_for_update()
        assert result.check_failed is True
        assert result.update_available is False

    def test_falls_back_to_version_file(self):
        with patch(
            "brush_watermark.services.update_check.fetch_latest_release",
            side_effect=OSError("api down"),
        ), patch(
            "brush_watermark.services.update_check.fetch_remote_version",
            return_value="2.0.0",
        ):
            result = check_for_update()
        assert result.latest_version == "2.0.0"
        assert result.download_url is None
        assert result.update_available is True


class TestAutoUpdateHelpers:
    def test_format_exe_args_quotes_paths(self):
        formatted = format_exe_args([r"C:\photos\my image.jpg"])
        assert "my image.jpg" in formatted

    def test_format_ps_argument_list_quotes_paths(self):
        formatted = format_ps_argument_list([r"C:\photos\my image.jpg"])
        assert formatted == r"'C:\photos\my image.jpg'"

    def test_format_ps_argument_list_empty(self):
        assert format_ps_argument_list([]) == ""

    def test_build_updater_script_contains_paths(self, tmp_path: Path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        exe = tmp_path / "BrushWatermark.exe"
        source.mkdir()
        target.mkdir()
        exe.write_text("", encoding="utf-8")

        script = build_updater_script(
            process_id=1234,
            source_dir=source,
            target_dir=target,
            exe_path=exe,
            exe_args=[r"C:\photos\test.jpg"],
        )
        text = script.read_text(encoding="utf-8")
        assert "Wait-Process -Id 1234" in text
        assert str(source) in text
        assert str(target) in text
        assert str(exe) in text
        assert f'-WorkingDirectory "{target}"' in text
        assert "-ArgumentList 'C:\\photos\\test.jpg'" in text

    def test_build_updater_script_omits_argument_list_when_empty(self, tmp_path: Path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        exe = tmp_path / "BrushWatermark.exe"
        source.mkdir()
        target.mkdir()
        exe.write_text("", encoding="utf-8")

        script = build_updater_script(
            process_id=999,
            source_dir=source,
            target_dir=target,
            exe_path=exe,
            exe_args=[],
        )
        text = script.read_text(encoding="utf-8")
        assert "-ArgumentList" not in text
        assert f'-WorkingDirectory "{target}"' in text

    def test_extract_update_finds_app_root(self, tmp_path: Path):
        archive = tmp_path / "BrushWatermark.zip"
        extract_dir = tmp_path / "extracted"
        app_root = tmp_path / "package" / "BrushWatermark"
        app_root.mkdir(parents=True)
        (app_root / "BrushWatermark.exe").write_text("", encoding="utf-8")

        with zipfile.ZipFile(archive, "w") as handle:
            for path in app_root.rglob("*"):
                handle.write(path, path.relative_to(tmp_path / "package").as_posix())

        found = extract_update(archive, extract_dir)
        assert found == extract_dir / "BrushWatermark"
        assert (found / "BrushWatermark.exe").exists()

    @pytest.mark.parametrize(
        ("frozen", "platform", "expected"),
        [
            (True, "win32", True),
            (False, "win32", False),
            (True, "linux", False),
        ],
    )
    def test_can_auto_update(self, frozen: bool, platform: str, expected: bool):
        with patch.object(sys, "frozen", frozen, create=True), patch.object(sys, "platform", platform):
            assert can_auto_update() is expected

    def test_install_directory_when_frozen(self, tmp_path: Path):
        exe = tmp_path / "BrushWatermark.exe"
        exe.write_text("", encoding="utf-8")
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(exe)):
            assert install_directory() == tmp_path
