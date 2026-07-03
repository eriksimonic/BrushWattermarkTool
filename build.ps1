# Build a folder-based Windows app (faster startup than single-file PyInstaller).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing build dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

Write-Host "Cleaning previous build outputs..."
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist

Write-Host "Building BrushWatermark (onedir, windowed)..."
$version = python -c "from brush_watermark import __version__; print(__version__)"
Write-Host "  Version: $version"
python -m PyInstaller --noconfirm --clean BrushWatermark.spec

$appDir = Join-Path $PSScriptRoot "dist\BrushWatermark"
$exe = Join-Path $appDir "BrushWatermark.exe"
if (-not (Test-Path $exe)) {
    throw "Build failed: $exe was not created."
}

$totalBytes = (Get-ChildItem $appDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
$totalMb = [math]::Round($totalBytes / 1MB, 1)
$exeMb = [math]::Round((Get-Item $exe).Length / 1MB, 1)

$zipPath = Join-Path $PSScriptRoot "dist\BrushWatermark.zip"
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path $appDir -DestinationPath $zipPath -Force
$zipMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)

Write-Host ""
Write-Host "Done."
Write-Host "  App folder: $appDir"
Write-Host "  Launcher:   $exe ($exeMb MB)"
Write-Host "  Total size: $totalMb MB (uncompressed folder)"
Write-Host "  Zip:        $zipPath ($zipMb MB)"
Write-Host ""
Write-Host "Usage: dist\BrushWatermark\BrushWatermark.exe path\to\image.jpg"
