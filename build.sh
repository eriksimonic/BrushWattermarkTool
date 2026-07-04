#!/usr/bin/env bash
# Build a folder-based app (faster startup than single-file PyInstaller).
set -euo pipefail
cd "$(dirname "$0")"

echo "Installing build dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo "Cleaning previous build outputs..."
rm -rf build dist

version="$(python -c "from brush_watermark import __version__; print(__version__)")"
echo "Building BrushWatermark (onedir, windowed)..."
echo "  Version: $version"
python -m PyInstaller --noconfirm --clean BrushWatermark.spec

case "$(uname -s)" in
  Darwin)
    app="dist/BrushWatermark.app"
    if [[ ! -d "$app" ]]; then
      echo "Build failed: $app was not created." >&2
      exit 1
    fi
    artifact="dist/BrushWatermark-macOS.zip"
    rm -f "$artifact"
    (cd dist && zip -r -y "$(basename "$artifact")" BrushWatermark.app)
    echo ""
    echo "Done."
    echo "  App bundle: $app"
    echo "  Zip:        $artifact"
    echo ""
    echo "Usage: open dist/BrushWatermark.app --args path/to/image.jpg"
    ;;
  Linux)
    app_dir="dist/BrushWatermark"
    exe="$app_dir/BrushWatermark"
    if [[ ! -f "$exe" ]]; then
      echo "Build failed: $exe was not created." >&2
      exit 1
    fi
    chmod +x "$exe"
    artifact="dist/BrushWatermark-Linux.tar.gz"
    rm -f "$artifact"
    tar -czf "$artifact" -C dist BrushWatermark
    echo ""
    echo "Done."
    echo "  App folder: $app_dir"
    echo "  Launcher:   $exe"
    echo "  Archive:    $artifact"
    echo ""
    echo "Usage: dist/BrushWatermark/BrushWatermark path/to/image.jpg"
    ;;
  *)
    echo "build.sh supports macOS and Linux only. On Windows, use build.ps1." >&2
    exit 1
    ;;
esac
