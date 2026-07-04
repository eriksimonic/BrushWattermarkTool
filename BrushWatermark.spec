# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — trimmed onedir build for faster startup and smaller footprint."""

import sys

block_cipher = None
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# Unused PySide6 modules (app only needs QtCore, QtGui, QtWidgets).
_PYSIDE6_UNUSED = [
    f"PySide6.{name}"
    for name in (
        "Qt3DAnimation", "Qt3DCore", "Qt3DExtras", "Qt3DInput", "Qt3DLogic", "Qt3DRender",
        "QtAsyncio", "QtAxContainer", "QtBluetooth", "QtCharts", "QtConcurrent",
        "QtDataVisualization", "QtDBus", "QtDesigner", "QtGraphs", "QtGraphsWidgets",
        "QtHelp", "QtHttpServer", "QtLocation", "QtMultimedia", "QtMultimediaWidgets",
        "QtNfc", "QtOpenGLWidgets", "QtPdf", "QtPdfWidgets", "QtPositioning",
        "QtPrintSupport", "QtQml", "QtQuick", "QtQuick3D", "QtQuickControls2",
        "QtQuickTest", "QtQuickWidgets", "QtRemoteObjects", "QtScxml", "QtSensors",
        "QtSerialBus", "QtSerialPort", "QtSpatialAudio", "QtSql", "QtStateMachine",
        "QtSvg", "QtSvgWidgets", "QtTest", "QtTextToSpeech", "QtUiTools",
        "QtWebChannel", "QtWebEngineCore", "QtWebEngineQuick", "QtWebEngineWidgets",
        "QtWebSockets", "QtWebView", "QtXml",
    )
]

_EXCLUDES = [
    "numpy",
    "tkinter",
    "pytest",
    "unittest",
    "test",
    "distutils",
    "setuptools",
    "pydoc",
    "doctest",
    "xmlrpc",
    "lib2to3",
    "PIL.ImageTk",
    "PIL._tkinter_finder",
    *_PYSIDE6_UNUSED,
]

_COMMON_DROP_FRAGMENTS = (
    "numpy",
    "numpy.libs",
    "pil/_imagingtk",
    "pil\\_imagingtk",
    "pil/_avif",
    "pil\\_avif",
    "charset_normalizer",
    "plugins/platforms/qoffscreen",
    "plugins/platforms/qminimal",
    "plugins/platforminputcontexts",
    "plugins/generic/qtuiotouch",
    "plugins/imageformats/qpdf",
    "plugins/imageformats/qicns",
    "plugins/imageformats/qtga",
    "plugins/imageformats/qwbmp",
    "plugins/imageformats/qtiff",
    "plugins/imageformats/qsvg",
    "plugins/iconengines",
    "plugins/tls/",
    "plugins/networkinformation",
)

_WIN_DROP_FRAGMENTS = _COMMON_DROP_FRAGMENTS + (
    "plugins/platforms/qdirect2d",
    "opengl32sw.dll",
)

_MAC_DROP_FRAGMENTS = _COMMON_DROP_FRAGMENTS

_LINUX_DROP_FRAGMENTS = _COMMON_DROP_FRAGMENTS

if IS_WIN:
    _DROP_BINARY_FRAGMENTS = _WIN_DROP_FRAGMENTS
elif IS_MAC:
    _DROP_BINARY_FRAGMENTS = _MAC_DROP_FRAGMENTS
else:
    _DROP_BINARY_FRAGMENTS = _LINUX_DROP_FRAGMENTS


def _norm(path: str) -> str:
    return path.replace("\\", "/").lower()


def _drop_artifact(name: str) -> bool:
    normalized = _norm(name)
    return any(fragment in normalized for fragment in _DROP_BINARY_FRAGMENTS)


if IS_WIN:
    _exe_icon = "brush_watermark/assets/icon.ico"
elif IS_MAC:
    _exe_icon = "brush_watermark/assets/icon.icns"
else:
    _exe_icon = None

a = Analysis(
    ["brush_watermark/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[("brush_watermark/assets/icon.png", "brush_watermark/assets")],
    hiddenimports=["PIL.ImageQt"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries = [entry for entry in a.binaries if not _drop_artifact(entry[0])]
a.datas = [entry for entry in a.datas if not _drop_artifact(entry[0])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_exe_kwargs = dict(
    exclude_binaries=True,
    name="BrushWatermark",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=IS_MAC,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
if _exe_icon:
    _exe_kwargs["icon"] = _exe_icon

exe = EXE(pyz, a.scripts, [], **_exe_kwargs)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BrushWatermark",
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name="BrushWatermark.app",
        icon="brush_watermark/assets/icon.icns",
        bundle_identifier="com.eriksimonic.brushwatermark",
    )
