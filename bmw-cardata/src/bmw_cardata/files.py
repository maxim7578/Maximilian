"""Private Dateien: nur für den eigenen Benutzer lesbar (Ordner 700, Dateien 600)."""

from __future__ import annotations

import errno
import os
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

try:  # POSIX
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]
try:  # Windows
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None  # type: ignore[assignment]

# Nicht auf jedem System vorhanden (z. B. Windows); dort entfällt der Schutz vor Links.
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
LOCK_TIMEOUT_SECONDS = 10.0
_LOCK_POLL_SECONDS = 0.05
# flock meldet EWOULDBLOCK/EAGAIN, msvcrt.locking EACCES bzw. EDEADLK (EDEADLOCK)
_LOCK_BUSY = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, errno.EDEADLK}


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)


def write_private(path: Path, text: str, errors: str = "strict") -> None:
    """Ersetzt die Datei atomar über eine eigene Zwischendatei (eindeutiger Name, Rechte 600).

    So bleibt nie eine halb geschriebene Fassung liegen, und zwei gleichzeitige Läufe
    kommen sich nicht über eine gemeinsame Zwischendatei in die Quere. errors wie bei open()
    (z. B. "surrogateescape", um ungültige Bytes unverändert zurückzuschreiben).
    """
    _ensure_parent(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors=errors) as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _check_own_file(fd: int, path: Path) -> None:
    """Bricht ab, wenn die Datei einem anderen gehört; zu offene Rechte werden auf 600 gesetzt.

    Unter Windows gibt es weder Benutzer-IDs noch Unix-Rechte (und os.fchmod erst ab
    Python 3.13); dort schützt das Benutzerprofil die Dateien.
    """
    if not hasattr(os, "getuid") or not hasattr(os, "fchmod"):
        return
    info = os.fstat(fd)
    if info.st_uid != os.getuid():
        raise PermissionError(f"{path} gehört einem anderen Benutzer.")
    if info.st_mode & 0o077:
        os.fchmod(fd, 0o600)


def append_private(path: Path, line: str) -> None:
    """Hängt eine Zeile an; folgt keinem Link und hält die Datei bei Rechten 600."""
    _ensure_parent(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | _NOFOLLOW, 0o600)
    try:
        _check_own_file(fd, path)
    except BaseException:
        os.close(fd)
        raise
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


class LockTimeout(OSError):
    """Die Sperre einer Datei wurde in der erlaubten Wartezeit nicht frei."""


def lock_path(path: Path) -> Path:
    """Versteckte Sperrdatei neben path, z. B. .verlauf.jsonl.lock."""
    return path.with_name(f".{path.name}.lock")


def _open_lock(lock: Path) -> int:
    if lock.is_symlink():  # auch dort, wo es kein O_NOFOLLOW gibt
        raise OSError(errno.ELOOP, "Die Sperrdatei ist ein symbolischer Link", str(lock))
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | _NOFOLLOW, 0o600)
    try:
        _check_own_file(fd, lock)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _try_lock(fd: int) -> bool:
    """Exklusive Sperre ohne zu warten; False, wenn ein anderer sie hält."""
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    except OSError as error:
        if error.errno in _LOCK_BUSY:
            return False
        raise
    return True


def _unlock(fd: int) -> None:
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)
    else:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


def _still_current(fd: int, lock: Path) -> bool:
    """Gehört die gesperrte Datei noch zum Namen? Nach dem Entfernen durch den Vorgänger nicht mehr."""
    try:
        named = os.lstat(lock)
    except FileNotFoundError:
        return False
    held = os.fstat(fd)
    return (named.st_dev, named.st_ino) == (held.st_dev, held.st_ino)


def _acquire(path: Path, lock: Path) -> int:
    timeout = LOCK_TIMEOUT_SECONDS
    deadline = time.monotonic() + timeout
    while True:
        fd = _open_lock(lock)
        try:
            if _try_lock(fd):
                # Unter Windows lässt sich eine offene Sperrdatei nicht entfernen, also kein Abgleich nötig.
                if fcntl is None or _still_current(fd, lock):
                    return fd
                _unlock(fd)
        except BaseException:
            os.close(fd)
            raise
        os.close(fd)
        if time.monotonic() >= deadline:
            message = (
                f"Die Datei ist gerade von einem anderen Vorgang gesperrt (länger als {timeout:g} s), "
                "z. B. von einem laufenden 'live --speichern'; bitte gleich noch einmal versuchen"
            )
            raise LockTimeout(errno.EBUSY, message, str(path))
        time.sleep(_LOCK_POLL_SECONDS)


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Sperrt path gegen andere Schreibvorgänge (auch aus anderen Prozessen) über eine Sperrdatei.

    Die Sperrdatei (Rechte 600, kein Link) wird danach wieder entfernt: unter POSIX noch
    während der Sperre (Wartende merken am geänderten Inode, dass sie neu öffnen müssen),
    unter Windows erst nach dem Schließen; dort scheitert das, solange ein anderer sie offen
    hat, und sie bleibt leer liegen. Wird die Sperre nicht binnen LOCK_TIMEOUT_SECONDS frei,
    folgt LockTimeout (ein OSError) mit verständlicher Meldung.
    """
    _ensure_parent(path)
    lock = lock_path(path)
    fd = _acquire(path, lock)
    try:
        yield
    finally:
        if fcntl is not None:
            with suppress(OSError):
                lock.unlink()
        try:
            _unlock(fd)
        finally:
            os.close(fd)
        if fcntl is None:
            with suppress(OSError):
                lock.unlink()
