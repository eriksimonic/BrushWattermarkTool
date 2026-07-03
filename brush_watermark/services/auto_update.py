import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

ProgressCallback = Callable[[int, str], None]


def can_auto_update() -> bool:
    return getattr(sys, "frozen", False) and sys.platform == "win32"


def install_directory() -> Path | None:
    if not can_auto_update():
        return None
    return Path(sys.executable).resolve().parent


def executable_path() -> Path | None:
    if not can_auto_update():
        return None
    return Path(sys.executable).resolve()


def _emit(progress: ProgressCallback | None, percent: int, message: str) -> None:
    if progress is not None:
        progress(max(0, min(100, percent)), message)


def download_update(
    url: str,
    destination: Path,
    *,
    progress: ProgressCallback | None = None,
    timeout: float = 120.0,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "BrushWatermark-Updater"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 256 * 1024
        with open(destination, "wb") as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    percent = int(downloaded * 100 / total)
                    _emit(progress, percent, f"Downloading update… {percent}%")
                else:
                    _emit(progress, 50, "Downloading update…")
    _emit(progress, 100, "Download complete")
    return destination


def extract_update(
    archive_path: Path,
    destination_dir: Path,
    *,
    progress: ProgressCallback | None = None,
) -> Path:
    _emit(progress, 0, "Extracting update…")
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination_dir)

    candidates = sorted(destination_dir.rglob("BrushWatermark.exe"))
    if not candidates:
        raise ValueError("Update archive does not contain BrushWatermark.exe")

    app_root = candidates[0].parent
    _emit(progress, 100, "Update ready")
    return app_root


def format_exe_args(argv: list[str]) -> str:
    return subprocess.list2cmdline(argv)


def build_updater_script(
    *,
    process_id: int,
    source_dir: Path,
    target_dir: Path,
    exe_path: Path,
    exe_args: list[str],
) -> Path:
    script_dir = Path(tempfile.gettempdir()) / "BrushWatermark-update"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / f"apply-update-{process_id}.ps1"
    args_text = format_exe_args(exe_args)

    script = f"""$ErrorActionPreference = 'SilentlyContinue'
try {{
    Wait-Process -Id {process_id}
}} catch {{}}
Start-Sleep -Seconds 2
& robocopy "{source_dir}" "{target_dir}" /E /IS /IT /R:5 /W:2 /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) {{ exit 1 }}
Start-Process -FilePath "{exe_path}" -ArgumentList '{args_text}'
"""
    script_path.write_text(script, encoding="utf-8")
    return script_path


def launch_updater(script_path: Path) -> None:
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script_path),
        ],
        close_fds=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def prepare_and_launch_update(
    download_url: str,
    *,
    process_id: int,
    exe_args: list[str] | None = None,
    progress: ProgressCallback | None = None,
) -> None:
    target_dir = install_directory()
    exe_path = executable_path()
    if target_dir is None or exe_path is None:
        raise RuntimeError("Auto-update is only available in the packaged Windows app.")

    work_dir = Path(tempfile.gettempdir()) / "BrushWatermark-update" / str(process_id)
    archive_path = work_dir / UPDATE_ASSET_FILENAME
    extract_dir = work_dir / "extracted"

    download_update(download_url, archive_path, progress=progress)
    source_dir = extract_update(archive_path, extract_dir, progress=progress)
    script_path = build_updater_script(
        process_id=process_id,
        source_dir=source_dir,
        target_dir=target_dir,
        exe_path=exe_path,
        exe_args=exe_args or [],
    )
    launch_updater(script_path)
    os._exit(0)


from brush_watermark.config import UPDATE_ASSET_FILENAME