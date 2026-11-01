"""Sperre um alle Schreibvorgänge auf den Verlauf (Anhängen, Aufräumen, Löschen)."""

import errno
import io
import os
import threading

import pytest
from conftest import VIN, ist_privat, nur_posix

import bmw_cardata.history as verlauf
from bmw_cardata import cli, files
from bmw_cardata.files import LockTimeout, lock_path, locked
from bmw_cardata.history import (
    Entry,
    append_entry,
    delete_history,
    load_entries,
    prune_entries,
)

JETZT = 1_793_534_400.0  # 01.11.2026 12:00 UTC
WARTEZEIT = 5  # Sekunden; nur eine Obergrenze, damit ein Fehler den Lauf nicht aufhängt


def _eintrag(zeit, km):
    return Entry(zeit, VIN, {"vehicle.vehicle.travelledDistance": {"value": km, "unit": "km"}})


ALT = _eintrag("2001-01-01T00:00:00Z", 1)
JUNG = _eintrag("2026-10-31T10:00:00Z", 2)
NEU = _eintrag("2026-11-01T11:00:00Z", 3)


@pytest.fixture
def wartet(monkeypatch):
    """Wird gesetzt, sobald ein Vorgang an der belegten Sperre warten muss."""
    ereignis = threading.Event()
    original = files._try_lock

    def versuch(fd):
        frei = original(fd)
        if not frei:
            ereignis.set()
        return frei

    monkeypatch.setattr(files, "_try_lock", versuch)
    return ereignis


class _Faden(threading.Thread):
    """Führt eine Funktion nebenläufig aus und merkt sich Ergebnis bzw. Fehler."""

    def __init__(self, funktion, *argumente):
        super().__init__(daemon=True)
        self.funktion, self.argumente = funktion, argumente
        self.ergebnis, self.fehler = None, None

    def run(self):
        try:
            self.ergebnis = self.funktion(*self.argumente)
        except BaseException as fehler:  # noqa: BLE001 – im Test auswerten
            self.fehler = fehler

    def fertig(self):
        self.join(WARTEZEIT)
        assert not self.is_alive(), "der nebenläufige Vorgang hängt"
        if self.fehler:
            raise self.fehler
        return self.ergebnis


def _verlauf_mit_altem_und_jungem_eintrag(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, ALT)
    append_entry(pfad, JUNG)
    return pfad


def test_anhängen_wartet_bis_die_sperre_frei_ist(tmp_path, wartet):
    pfad = tmp_path / "verlauf.jsonl"
    with locked(pfad):
        faden = _Faden(append_entry, pfad, NEU)
        faden.start()
        assert wartet.wait(WARTEZEIT)
        assert not pfad.exists()  # noch nichts geschrieben
    faden.fertig()
    assert load_entries(pfad) == [NEU]


def test_anhängen_während_des_aufräumens_geht_nicht_verloren(tmp_path, monkeypatch, wartet):
    pfad = _verlauf_mit_altem_und_jungem_eintrag(tmp_path)
    echtes_schreiben = verlauf.write_private
    gestartet = []

    def schreiben_mit_parallelem_anhängen(*argumente, **optionen):
        faden = _Faden(append_entry, pfad, NEU)
        faden.start()
        gestartet.append(faden)
        assert wartet.wait(WARTEZEIT), "das Anhängen hätte auf das Aufräumen warten müssen"
        echtes_schreiben(*argumente, **optionen)

    monkeypatch.setattr(verlauf, "write_private", schreiben_mit_parallelem_anhängen)
    assert prune_entries(pfad, 365, JETZT) == 1
    gestartet[0].fertig()
    assert load_entries(pfad) == [JUNG, NEU]


def test_aufräumen_stellt_einen_währenddessen_gelöschten_verlauf_nicht_wieder_her(tmp_path, monkeypatch, wartet):
    pfad = _verlauf_mit_altem_und_jungem_eintrag(tmp_path)
    echtes_schreiben = verlauf.write_private
    gestartet = []

    def schreiben_mit_parallelem_löschen(*argumente, **optionen):
        faden = _Faden(delete_history, pfad)
        faden.start()
        gestartet.append(faden)
        assert wartet.wait(WARTEZEIT), "das Löschen hätte auf das Aufräumen warten müssen"
        echtes_schreiben(*argumente, **optionen)

    monkeypatch.setattr(verlauf, "write_private", schreiben_mit_parallelem_löschen)
    assert prune_entries(pfad, 365, JETZT) == 1
    assert gestartet[0].fertig() is True
    assert not pfad.exists()
    assert list(tmp_path.iterdir()) == []  # weder Zwischen- noch Sperrdatei


def test_aufräumen_nach_dem_löschen_legt_den_verlauf_nicht_neu_an(tmp_path, wartet):
    pfad = _verlauf_mit_altem_und_jungem_eintrag(tmp_path)
    with locked(pfad):  # wie ein laufendes 'verlauf --loeschen'
        faden = _Faden(prune_entries, pfad, 365, JETZT)
        faden.start()
        assert wartet.wait(WARTEZEIT)
        pfad.unlink()
    assert faden.fertig() == 0
    assert not pfad.exists()


def test_belegte_sperre_führt_nach_kurzer_wartezeit_zu_einem_verständlichen_fehler(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "LOCK_TIMEOUT_SECONDS", 0.2)
    pfad = tmp_path / "verlauf.jsonl"
    with locked(pfad), pytest.raises(LockTimeout) as fehler:
        append_entry(pfad, NEU)
    assert isinstance(fehler.value, OSError)
    assert "gerade von einem anderen Vorgang gesperrt" in fehler.value.strerror
    assert "noch einmal versuchen" in fehler.value.strerror
    assert fehler.value.filename == str(pfad)
    assert not pfad.exists()


def test_verlauf_löschen_bei_belegter_sperre_meldet_den_fehler_und_löscht_nichts(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "LOCK_TIMEOUT_SECONDS", 0.2)
    zustand = tmp_path / "state.json"
    pfad = _verlauf_mit_altem_und_jungem_eintrag(tmp_path)
    aus, fehler = io.StringIO(), io.StringIO()
    with locked(pfad):
        code = cli.run(["--state", str(zustand), "verlauf", "--loeschen"], out=aus, err=fehler)
    assert code == 1
    assert "Dateifehler:" in fehler.getvalue() and "gesperrt" in fehler.getvalue()
    assert load_entries(pfad) == [ALT, JUNG]


def test_sperrdatei_liegt_versteckt_neben_dem_verlauf_und_verschwindet_danach(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    assert lock_path(pfad) == tmp_path / ".verlauf.jsonl.lock"
    with locked(pfad):
        assert lock_path(pfad).exists()
        assert ist_privat(lock_path(pfad))
    assert not lock_path(pfad).exists()


def test_liegengebliebene_sperrdatei_blockiert_nicht_und_wird_beim_löschen_entfernt(tmp_path):
    pfad = tmp_path / "verlauf.jsonl"
    lock_path(pfad).write_text("")  # z. B. nach einem Absturz; die Sperre selbst ist frei
    append_entry(pfad, NEU)
    lock_path(pfad).write_text("")
    assert delete_history(pfad) is True
    assert list(tmp_path.iterdir()) == []


def test_löschen_ohne_ordner_legt_nichts_an(tmp_path):
    pfad = tmp_path / "fehlt" / "verlauf.jsonl"
    assert delete_history(pfad) is False
    assert not pfad.parent.exists()


@nur_posix
def test_sperrdatei_folgt_keinem_symbolischen_link(tmp_path):
    ziel = tmp_path / "anderswo.txt"
    ziel.write_text("unverändert")
    pfad = tmp_path / "verlauf.jsonl"
    lock_path(pfad).symlink_to(ziel)
    with pytest.raises(OSError) as fehler:
        append_entry(pfad, NEU)
    assert fehler.value.errno == errno.ELOOP
    assert ziel.read_text() == "unverändert"
    assert not pfad.exists()


@nur_posix
def test_sperre_merkt_wenn_ihre_datei_inzwischen_ersetzt_wurde(tmp_path):
    sperre = tmp_path / ".verlauf.jsonl.lock"
    sperre.write_text("")
    fd = os.open(sperre, os.O_RDWR)
    try:
        assert files._still_current(fd, sperre)
        sperre.unlink()
        assert not files._still_current(fd, sperre)
        sperre.write_text("")  # neue Datei unter demselben Namen
        assert not files._still_current(fd, sperre)
    finally:
        os.close(fd)


class _FalschesMsvcrt:
    """Nachbildung von msvcrt.locking für den Windows-Zweig."""

    LK_UNLCK, LK_NBLCK = 0, 2

    def __init__(self, belegt=False):
        self.belegt, self.aufrufe = belegt, []

    def locking(self, fd, modus, anzahl):
        self.aufrufe.append((modus, anzahl, os.lseek(fd, 0, os.SEEK_CUR)))
        if self.belegt and modus == self.LK_NBLCK:
            raise OSError(errno.EACCES, "Permission denied")


def test_unter_windows_sperrt_msvcrt_das_erste_byte_und_entfernt_die_sperrdatei_danach(tmp_path, monkeypatch):
    falsch = _FalschesMsvcrt()
    monkeypatch.setattr(files, "fcntl", None)
    monkeypatch.setattr(files, "msvcrt", falsch)
    pfad = tmp_path / "verlauf.jsonl"
    append_entry(pfad, NEU)
    assert falsch.aufrufe == [(falsch.LK_NBLCK, 1, 0), (falsch.LK_UNLCK, 1, 0)]
    assert load_entries(pfad) == [NEU]
    assert not lock_path(pfad).exists()


def test_unter_windows_führt_eine_belegte_sperre_zum_verständlichen_fehler(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "fcntl", None)
    monkeypatch.setattr(files, "msvcrt", _FalschesMsvcrt(belegt=True))
    monkeypatch.setattr(files, "LOCK_TIMEOUT_SECONDS", 0.1)
    pfad = tmp_path / "verlauf.jsonl"
    with pytest.raises(LockTimeout, match="gesperrt"):
        append_entry(pfad, NEU)
    assert not pfad.exists()
