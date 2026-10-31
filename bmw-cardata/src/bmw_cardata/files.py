"""Private Dateien: nur für den eigenen Benutzer lesbar (Ordner 700, Dateien 600)."""

from __future__ import annotations

import os
from pathlib import Path


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)


def write_private(path: Path, text: str) -> None:
    """Ersetzt die Datei atomar, damit nie eine halb geschriebene Fassung liegen bleibt."""
    _ensure_parent(path)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp, path)


def append_private(path: Path, line: str) -> None:
    """Hängt eine Zeile an; eine neue Datei entsteht mit Rechten 600."""
    _ensure_parent(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
