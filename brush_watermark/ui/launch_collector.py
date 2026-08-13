"""Merges near-simultaneous single-file launches into one window.

Explorer's shell verb model launches this app once per selected file
instead of once with every path, and Windows doesn't reliably honor
`MultiSelectModel=Player` (confirmed by hand: it silently does nothing,
under both `SystemFileAssociations\\<ext>\\shell` and `*\\shell` with an
`AppliesTo` filter). So when the app is started with CLI file arguments,
one process becomes the primary window and sibling processes launched
within a short window hand it their paths instead of opening their own
window.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "BrushWatermarkLaunchCollector"
CONNECT_TIMEOUT_MS = 300
LISTEN_RETRY_ATTEMPTS = 10
LISTEN_RETRY_DELAY_MS = 100
COLLECT_WINDOW_MS = 8000


def _forward_to_running_instance(image_paths: list[Path]) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(CONNECT_TIMEOUT_MS):
        return False
    payload = "\n".join(str(path) for path in image_paths).encode("utf-8")
    socket.write(payload)
    socket.waitForBytesWritten(1000)
    socket.disconnectFromServer()
    return True


def claim_primary_or_forward(image_paths: list[Path]) -> tuple[bool, QLocalServer | None]:
    """Coordinate with sibling launches of this process.

    Returns (forwarded, server). If forwarded is True, image_paths were
    handed to another instance and this process should exit without
    opening a window. Otherwise this process should open its own window;
    server is a listening QLocalServer to pass to start_collecting() (or
    None if listening failed and this window should just run solo).
    """
    if _forward_to_running_instance(image_paths):
        return True, None

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if server.listen(SERVER_NAME):
        return False, server

    # Lost the race between our failed connect attempt and someone else's
    # listen() call in between. Retry forwarding before giving up.
    for _ in range(LISTEN_RETRY_ATTEMPTS):
        time.sleep(LISTEN_RETRY_DELAY_MS / 1000)
        if _forward_to_running_instance(image_paths):
            return True, None
    return False, None


def start_collecting(server: QLocalServer, on_paths_received: Callable[[list[Path]], None]) -> None:
    """Wire up a listening server to forward incoming paths for a bounded window."""

    def _handle_new_connection() -> None:
        connection = server.nextPendingConnection()
        if connection is None:
            return

        def _handle_ready_read() -> None:
            data = bytes(connection.readAll()).decode("utf-8", errors="ignore")
            paths = [Path(line) for line in data.splitlines() if line.strip()]
            if paths:
                on_paths_received(paths)
            connection.disconnectFromServer()

        connection.readyRead.connect(_handle_ready_read)

    server.newConnection.connect(_handle_new_connection)
    QTimer.singleShot(COLLECT_WINDOW_MS, server.close)
