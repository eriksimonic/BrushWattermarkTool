import subprocess
import sys
from pathlib import Path

from brush_watermark.config import APP_SLUG

MENU_TEXT = "Watermark Image"
SUPPORTED_CONTEXT_EXTENSIONS = (".jpg", ".jpeg")
FILE_PLACEHOLDER = "%1"


def _quote_command_arg(arg: str) -> str:
    if arg == FILE_PLACEHOLDER:
        return f'"{FILE_PLACEHOLDER}"'
    return subprocess.list2cmdline([arg])


def build_launch_command(image_arg: str = FILE_PLACEHOLDER) -> str:
    args = [sys.executable]
    if getattr(sys, "frozen", False):
        args.append(image_arg)
    else:
        source_launcher = Path(__file__).resolve().parents[2] / "brush_watermark.py"
        if source_launcher.is_file():
            args.extend([str(source_launcher), image_arg])
        else:
            args.extend(["-m", "brush_watermark", image_arg])
    return " ".join(_quote_command_arg(str(arg)) for arg in args)


def _icon_location() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    icon_path = Path(__file__).resolve().parents[1] / "assets" / "icon.ico"
    return str(icon_path)


def _context_key(extension: str) -> str:
    return rf"Software\Classes\SystemFileAssociations\{extension}\shell\{APP_SLUG}"


def install_context_menu() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Explorer context menu integration is only available on Windows.")

    import winreg

    command = build_launch_command()
    icon = _icon_location()
    for extension in SUPPORTED_CONTEXT_EXTENSIONS:
        key_path = _context_key(extension)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, MENU_TEXT)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command") as command_key:
            winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)


def uninstall_context_menu() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Explorer context menu integration is only available on Windows.")

    import winreg

    for extension in SUPPORTED_CONTEXT_EXTENSIONS:
        key_path = _context_key(extension)
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + r"\command")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass
