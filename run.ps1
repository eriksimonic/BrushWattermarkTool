# Runs BrushWatermark using the project's virtual environment.
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found, creating one at .venv ..."
    python -m venv (Join-Path $root ".venv")
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $root "requirements.txt")
}

& $venvPython (Join-Path $root "brush_watermark.py") @args
exit $LASTEXITCODE
