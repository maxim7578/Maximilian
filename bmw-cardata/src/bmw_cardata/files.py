"""Private Dateien: nur für den eigenen Benutzer lesbar (Ordner 700, Dateien 600)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Nicht auf jedem System vorhanden (z. B. Windows); dort entfällt der Schutz vor Links.
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)


def write_private(path: Path, text: str) -> None:
    """Ersetzt die Datei atomar über eine eigene Zwischendatei (eindeutiger Name, Rechte 600).

    So bleibt nie eine halb geschriebene Fassung liegen, und zwei gleichzeitige Läufe
    kommen sich nicht über eine gemeinsame Zwischendatei in die Quere.
    """
    _ensure_parent(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
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
