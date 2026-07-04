import sys
from unittest.mock import patch

from brush_watermark.services.explorer_context import FILE_PLACEHOLDER, MENU_TEXT, build_launch_command


def test_menu_text_matches_explorer_label():
    assert MENU_TEXT == "Watermark Image"


def test_build_launch_command_quotes_frozen_exe_and_file_placeholder():
    exe = r"C:\Program Files\BrushWatermark\BrushWatermark.exe"
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", exe):
        command = build_launch_command()

    assert command == f'"{exe}" "{FILE_PLACEHOLDER}"'


def test_build_launch_command_uses_source_launcher_for_development():
    exe = r"C:\Program Files\Python313\python.exe"
    with patch.object(sys, "frozen", False, create=True), patch.object(sys, "executable", exe):
        command = build_launch_command()

    assert command.startswith(f'"{exe}" ')
    assert "brush_watermark.py" in command
    assert command.endswith(f' "{FILE_PLACEHOLDER}"')
