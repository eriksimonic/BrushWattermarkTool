import sys
from unittest.mock import MagicMock, patch

from brush_watermark.services.explorer_context import (
    FILE_PLACEHOLDER,
    MENU_TEXT,
    SUPPORTED_CONTEXT_EXTENSIONS,
    build_launch_command,
    uninstall_context_menu,
)


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


def test_uninstall_deletes_parent_key_even_when_command_subkey_is_missing():
    """A missing `\\command` subkey must not stop the parent key delete."""
    fake_winreg = MagicMock()

    def delete_key(_root, key_path):
        if key_path.endswith(r"\command"):
            raise FileNotFoundError
        # Parent key delete should still be attempted and succeed.

    fake_winreg.DeleteKey.side_effect = delete_key

    with patch.object(sys, "platform", "win32"), patch.dict(sys.modules, {"winreg": fake_winreg}):
        uninstall_context_menu()

    # One command-subkey delete attempt and one parent-key delete attempt per extension.
    assert fake_winreg.DeleteKey.call_count == 2 * len(SUPPORTED_CONTEXT_EXTENSIONS)
    parent_calls = [
        call for call in fake_winreg.DeleteKey.call_args_list if not call.args[1].endswith(r"\command")
    ]
    assert len(parent_calls) == len(SUPPORTED_CONTEXT_EXTENSIONS)
