# Build a single self-contained Windows executable (one .exe, no _internal folder).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing build dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

Write-Host "Cleaning previous build outputs..."
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist

Write-Host "Building BrushWatermark.exe (single-file, windowed)..."
$version = python -c "from brush_watermark import __version__; print(__version__)"
Write-Host "  Version: $version"
python -m PyInstaller --noconfirm --clean BrushWatermark.spec

$exe = Join-Path $PSScriptRoot "dist\BrushWatermark.exe"
if (-not (Test-Path $exe)) {
    throw "Build failed: $exe was not created."
}

$sizeMb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host ""
Write-Host "Done."
Write-Host "  Output: $exe"
Write-Host "  Size:   $sizeMb MB"
Write-Host ""
Write-Host "Usage: BrushWatermark.exe path\to\image.jpg"
