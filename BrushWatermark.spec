# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — trimmed onedir build for faster startup and smaller footprint."""

block_cipher = None

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

# Qt / PIL artifacts not needed for a JPG watermark tool on Windows.
_DROP_BINARY_FRAGMENTS = (
    "numpy",
    "numpy.libs",
    "pil/_imagingtk",
    "pil\\_imagingtk",
    "pil/_avif",
    "pil\\_avif",
    "charset_normalizer",
    "plugins/platforms/qoffscreen",
    "plugins/platforms/qminimal",
    "plugins/platforms/qdirect2d",
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
    "opengl32sw.dll",
)


def _norm(path: str) -> str:
    return path.replace("\\", "/").lower()


def _drop_artifact(name: str) -> bool:
    normalized = _norm(name)
    return any(fragment in normalized for fragment in _DROP_BINARY_FRAGMENTS)


a = Analysis(
    ["brush_watermark/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[],
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

exe = EXE(
    pyz,
    a.scripts,
    [],
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

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
