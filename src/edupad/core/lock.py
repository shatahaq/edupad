"""Kunci proses tunggal. Dilepas otomatis oleh OS saat proses selesai atau crash."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class AlreadyRunning(RuntimeError):
    pass


def acquire_lock(path: Path) -> int:
    """Kembalikan file descriptor; jangan ditutup selama kunci dibutuhkan."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    try:
        if sys.platform == "win32":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        raise AlreadyRunning(f"proses lain sedang memakai {path.name}") from None
    return fd


def release_lock(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    os.close(fd)


@contextmanager
def wait_for_lock(path: Path, timeout: float = 120, poll: float = 1) -> Iterator[None]:
    """Seperti acquire_lock, tapi menunggu giliran; AlreadyRunning bila melewati timeout."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = acquire_lock(path)
            break
        except AlreadyRunning:
            if time.monotonic() >= deadline:
                raise
            time.sleep(poll)
    try:
        yield
    finally:
        release_lock(fd)
