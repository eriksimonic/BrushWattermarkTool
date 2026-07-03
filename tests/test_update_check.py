from unittest.mock import patch

from brush_watermark.services.update_check import (
    UpdateCheckResult,
    check_for_update,
    is_newer_version,
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


class TestCheckForUpdate:
    def test_update_available(self):
        with patch(
            "brush_watermark.services.update_check.fetch_remote_version",
            return_value="9.0.0",
        ):
            result = check_for_update()
        assert result.update_available is True
        assert result.latest_version == "9.0.0"
        assert result.check_failed is False

    def test_up_to_date(self):
        with patch(
            "brush_watermark.services.update_check.fetch_remote_version",
            return_value="1.0.0",
        ):
            result = check_for_update()
        assert result.update_available is False
        assert isinstance(result, UpdateCheckResult)

    def test_network_failure(self):
        with patch(
            "brush_watermark.services.update_check.fetch_remote_version",
            side_effect=OSError("offline"),
        ):
            result = check_for_update()
        assert result.check_failed is True
        assert result.update_available is False
