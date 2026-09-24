"""Merges near-simultaneous single-file launches into one window.

Explorer's shell verb model launches this app once per selected file
instead of once with every path, and Windows doesn't reliably honor
`MultiSelectModel=Player` (confirmed by hand: it silently does nothing,
under both `SystemFileAssociations\\<ext>\\shell` and `*\\shell` with an
`AppliesTo` filter). So when the app is started with CLI file arguments,
one process becomes the primary window and sibling processes launched
within a short window hand it their paths instead of opening their own
window.

Who becomes primary is decided by a lock file, not by who manages to
`listen()` first: on Windows several processes can listen on the same
pipe name, and the primary can't accept more than one connection until
its event loop is running, so a connect timeout alone doesn't prove
nobody else is primary. Siblings that lose the lock keep retrying the
connect until the primary is serving.
"""
from __future__ import annotations

import getpass
import time
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QDir, QEventLoop, QLockFile, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket

APP_ID = "BrushWatermarkLaunchCollector"
CONNECT_TIMEOUT_MS = 250
IO_TIMEOUT_MS = 2000
ACK_TIMEOUT_MS = 3000
RETRY_DELAY_S = 0.1
# Generous enough to cover a slow (cold PyInstaller) primary start-up.
FORWARD_DEADLINE_S = 20.0
COLLECT_WINDOW_MS = 8000
END_OF_PAYLOAD = b"\0"
ACK = b"ok"


def _user_suffix() -> str:
    # Pipe names are machine-wide on Windows; keep users' sessions apart.
    try:
        user = getpass.getuser()
    except Exception:
        user = ""
    return "".join(ch for ch in user if ch.isalnum()) or "user"


SERVER_NAME = f"{APP_ID}-{_user_suffix()}"


def _encode_paths(paths: list[Path]) -> bytes:
    return "\n".join(str(path) for path in paths).encode("utf-8")


def _decode_paths(data: bytes) -> list[Path]:
    text = data.decode("utf-8", errors="ignore")
    return [Path(line) for line in text.splitlines() if line.strip()]


def _forward_to_running_instance(image_paths: list[Path], ack_timeout_ms: int) -> bool:
    """Send paths to the primary; True only once it has acknowledged them.

    Occasionally a connection accepted right as the primary starts listening
    is never read, so the ack wait is bounded and the caller retries on a
    fresh connection. Re-sending is harmless: load_documents and
    MainWindow.add_documents skip paths that are already open.
    """
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(CONNECT_TIMEOUT_MS):
        return False
    socket.write(_encode_paths(image_paths) + END_OF_PAYLOAD)
    acked = socket.waitForBytesWritten(IO_TIMEOUT_MS) and socket.waitForReadyRead(ack_timeout_ms)
    acked = acked and bytes(socket.readAll()).startswith(ACK)
    socket.abort()
    return acked


class LaunchCollector:
    """Primary side: receives paths from sibling launches for a bounded window.

    Paths that arrive before a receiver is attached (while the primary is
    still loading its own images) are buffered and handed over by
    set_receiver().
    """

    def __init__(self, server: QLocalServer, lock: QLockFile):
        self._server = server
        # Held for as long as we're collecting; released in stop().
        self._lock = lock
        self._pending: list[Path] = []
        self._receiver: Optional[Callable[[list[Path]], None]] = None
        self._wake: Optional[Callable[[], None]] = None
        server.newConnection.connect(self._accept_connections)

    def set_receiver(self, receiver: Callable[[list[Path]], None]) -> None:
        """Attach the window and start the collect window's countdown."""
        self._receiver = receiver
        if self._pending:
            pending, self._pending = self._pending, []
            receiver(pending)
        QTimer.singleShot(COLLECT_WINDOW_MS, self.stop)

    def wait_for_paths(self) -> list[Path]:
        """Run a local event loop until a sibling hands over paths or the window lapses."""
        if not self._pending and self._server.isListening():
            loop = QEventLoop()
            timer = QTimer(loop)
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            timer.start(COLLECT_WINDOW_MS)
            self._wake = loop.quit
            loop.exec()
            self._wake = None
        paths, self._pending = self._pending, []
        return paths

    def stop(self) -> None:
        # Close before unlocking so a new primary never listens alongside us.
        self._server.close()
        self._lock.unlock()

    def _accept_connections(self) -> None:
        while (connection := self._server.nextPendingConnection()) is not None:
            buffer = bytearray()

            # Payloads can arrive in several chunks; deliver once the end marker is in.
            def _read(connection=connection, buffer=buffer) -> None:
                if END_OF_PAYLOAD in buffer:
                    return
                buffer.extend(bytes(connection.readAll()))
                if END_OF_PAYLOAD not in buffer:
                    return
                connection.write(ACK)
                connection.flush()
                self._deliver(_decode_paths(bytes(buffer[: buffer.index(END_OF_PAYLOAD)])))

            connection.readyRead.connect(_read)
            connection.disconnected.connect(connection.deleteLater)
            # Data may already be buffered before readyRead was connected.
            if connection.bytesAvailable():
                _read()

    def _deliver(self, paths: list[Path]) -> None:
        if not paths:
            return
        if self._receiver is not None:
            self._receiver(paths)
        else:
            self._pending.extend(paths)
            if self._wake is not None:
                self._wake()


def claim_primary_or_forward(image_paths: list[Path]) -> tuple[bool, Optional[LaunchCollector]]:
    """Coordinate with sibling launches of this process.

    Returns (forwarded, collector). If forwarded is True, image_paths were
    handed to another instance and this process should exit without
    opening a window. Otherwise this process opens its own window; collector
    is the primary's LaunchCollector (or None if coordination failed and
    this window should just run solo).
    """
    lock = QLockFile(QDir(QDir.tempPath()).filePath(f"{SERVER_NAME}.lock"))
    # Only a dead owner makes the lock stale; a slow primary may hold it >30 s.
    lock.setStaleLockTime(0)
    deadline = time.monotonic() + FORWARD_DEADLINE_S
    while time.monotonic() < deadline:
        if _forward_to_running_instance(image_paths, ACK_TIMEOUT_MS):
            return True, None
        if lock.tryLock(0):
            # Only the lock holder may touch the server name, so removing a
            # stale Unix socket file can't break a live primary.
            QLocalServer.removeServer(SERVER_NAME)
            server = QLocalServer()
            if server.listen(SERVER_NAME):
                return False, LaunchCollector(server, lock)
            lock.unlock()
            return False, None
        time.sleep(RETRY_DELAY_S)
    return False, None
