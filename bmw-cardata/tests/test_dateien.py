import os

import pytest

from bmw_cardata import files
from bmw_cardata.files import append_private, write_private


def test_fehler_beim_ersetzen_hinterlässt_keine_zwischendatei(tmp_path, monkeypatch):
    def kaputt(*args):
        raise OSError("Platte voll")

    monkeypatch.setattr(files.os, "replace", kaputt)
    with pytest.raises(OSError, match="Platte voll"):
        write_private(tmp_path / "state.json", "{}")
    assert list(tmp_path.iterdir()) == []


def test_datei_eines_anderen_benutzers_wird_nicht_beschrieben(tmp_path, monkeypatch):
    pfad = tmp_path / "verlauf.jsonl"
    pfad.write_text("fremd\n")
    offen_vorher = len(os.listdir("/proc/self/fd"))
    monkeypatch.setattr(files.os, "getuid", lambda: os.stat(pfad).st_uid + 1)
    with pytest.raises(PermissionError, match="anderen Benutzer"):
        append_private(pfad, "neu")
    assert pfad.read_text() == "fremd\n"
    assert len(os.listdir("/proc/self/fd")) == offen_vorher


def test_anhängen_ergänzt_zeilen(tmp_path):
    pfad = tmp_path / "unter" / "verlauf.jsonl"
    append_private(pfad, "eins")
    append_private(pfad, "zwei")
    assert pfad.read_text() == "eins\nzwei\n"
