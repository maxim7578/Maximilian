import os
import stat
from pathlib import Path

import pytest

from assistent.konfig import (
    KonfigFehler,
    besitzer_aus_umgebung,
    erzeugen,
    werte_aus_umgebung,
)

VORLAGEN = Path(__file__).parent.parent / "asterisk" / "vorlagen"
ENV = {
    "FRITZBOX_ADRESSE": "192.168.178.1",
    "FRITZBOX_BENUTZER": "kiassistent",
    "FRITZBOX_KENNWORT": "Geheim123",
    "ARI_KENNWORT": "nochGeheimer456",
}


def test_alle_platzhalter_ersetzt(tmp_path):
    dateien = erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung(ENV))
    assert len(dateien) >= 10
    for datei in dateien:
        assert "{{" not in datei.read_text(encoding="utf-8"), datei.name
    pjsip = (tmp_path / "pjsip.conf").read_text(encoding="utf-8")
    assert "client_uri = sip:kiassistent@192.168.178.1" in pjsip
    assert "password = Geheim123" in pjsip
    assert "bindaddr = 127.0.0.1" in (tmp_path / "http.conf").read_text(encoding="utf-8")


def test_eingehend_standardmaessig_aus(tmp_path):
    erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung(ENV))
    assert '$["aus" = "an"]' in (tmp_path / "extensions.conf").read_text(encoding="utf-8")
    erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung({**ENV, "EINGEHENDE_ANRUFE": "an"}))
    assert '$["an" = "an"]' in (tmp_path / "extensions.conf").read_text(encoding="utf-8")


@pytest.mark.parametrize("kennwort", ["mit leerzeichen", "semi;kolon", "HIER_KENNWORT", ""])
def test_ungueltige_werte(kennwort):
    with pytest.raises(KonfigFehler):
        werte_aus_umgebung({**ENV, "FRITZBOX_KENNWORT": kennwort})


def test_fritzbox_nur_an_der_ip_erkannt(tmp_path):
    """Ein gefälschter Absendername darf nicht reichen, um als FRITZ!Box zu gelten."""
    erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung(ENV))
    pjsip = (tmp_path / "pjsip.conf").read_text(encoding="utf-8")
    endpunkt = pjsip.split("[fritzbox]\ntype = endpoint", 1)[1].split("\n[", 1)[0]
    assert "identify_by = ip" in endpunkt



# ---------- Dateirechte (enthält das FRITZ!Box-Kennwort) ----------

ALS_ROOT = pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() != 0, reason="Besitzerwechsel geht nur als root"
)


def test_erzeugte_dateien_nur_fuer_besitzer_lesbar(tmp_path):
    ziel = tmp_path / "etc"
    dateien = erzeugen(VORLAGEN, ziel, werte_aus_umgebung(ENV))
    assert stat.S_IMODE(ziel.stat().st_mode) == 0o700
    for datei in dateien:
        assert stat.S_IMODE(datei.stat().st_mode) == 0o600, datei.name


def test_vorhandene_offene_dateien_werden_verschlossen(tmp_path):
    """Alte Installationen: pjsip.conf lag bisher mit 644 im Ordner (755)."""
    tmp_path.chmod(0o755)
    alt = tmp_path / "pjsip.conf"
    alt.write_text("alt", encoding="utf-8")
    alt.chmod(0o644)
    erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung(ENV))
    assert stat.S_IMODE(alt.stat().st_mode) == 0o600
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
    assert "password = Geheim123" in alt.read_text(encoding="utf-8")


def test_keine_reste_von_zwischendateien(tmp_path):
    erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung(ENV))
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(p.name for p in VORLAGEN.glob("*.conf"))


@ALS_ROOT
def test_als_root_gehoeren_dateien_dem_asterisk_benutzer(tmp_path, monkeypatch):
    """Asterisk läuft im Container als UID 1000 und muss die Dateien lesen können."""
    monkeypatch.delenv("PUID", raising=False)
    monkeypatch.delenv("PGID", raising=False)
    ziel = tmp_path / "etc"
    dateien = erzeugen(VORLAGEN, ziel, werte_aus_umgebung(ENV))
    for pfad in [ziel, *dateien]:
        assert (pfad.stat().st_uid, pfad.stat().st_gid) == (1000, 1000), pfad.name


@ALS_ROOT
def test_als_root_puid_und_pgid_aus_umgebung(tmp_path, monkeypatch):
    monkeypatch.setenv("PUID", "1234")
    monkeypatch.setenv("PGID", "2345")
    ziel = tmp_path / "etc"
    dateien = erzeugen(VORLAGEN, ziel, werte_aus_umgebung(ENV))
    for pfad in [ziel, *dateien]:
        assert (pfad.stat().st_uid, pfad.stat().st_gid) == (1234, 2345), pfad.name


def test_ohne_root_kein_besitzerwechsel(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 1000, raising=False)
    assert besitzer_aus_umgebung({"PUID": "1234"}) is None


def test_ohne_geteuid_wie_unter_windows(monkeypatch):
    monkeypatch.delattr(os, "geteuid", raising=False)
    assert besitzer_aus_umgebung({}) is None


def test_besitzer_standard_und_aus_umgebung(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
    assert besitzer_aus_umgebung({}) == (1000, 1000)
    assert besitzer_aus_umgebung({"PUID": "1234", "PGID": "2345"}) == (1234, 2345)


@pytest.mark.parametrize("puid", ["abc", "-5", "1.5"])
def test_ungueltige_puid(monkeypatch, puid):
    monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
    with pytest.raises(KonfigFehler):
        besitzer_aus_umgebung({"PUID": puid})


# ---------- Hartes Zeitlimit im Wählplan ----------


def _abschnitt(text: str, name: str) -> str:
    return text.split(f"[{name}]", 1)[1].split("\n[", 1)[0]


def test_hartes_zeitlimit_fuer_beide_richtungen(tmp_path):
    """Hängt die Pipeline, legt Asterisk spätestens MAX_GESPRAECH_SEKUNDEN + 60 s auf."""
    erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung(ENV))
    wahlplan = (tmp_path / "extensions.conf").read_text(encoding="utf-8")
    for abschnitt in ("ki-raus", "eingehend"):
        teil = _abschnitt(wahlplan, abschnitt)
        assert "Set(TIMEOUT(absolute)=360)" in teil, abschnitt
        assert teil.index("TIMEOUT(absolute)") < teil.index("Dial(WebSocket"), abschnitt


def test_zeitlimit_folgt_max_gespraech_sekunden(tmp_path):
    erzeugen(VORLAGEN, tmp_path, werte_aus_umgebung({**ENV, "MAX_GESPRAECH_SEKUNDEN": "120"}))
    assert "Set(TIMEOUT(absolute)=180)" in (tmp_path / "extensions.conf").read_text(encoding="utf-8")


@pytest.mark.parametrize("sekunden", ["abc", "0", "-10"])
def test_ungueltige_gespraechsdauer(sekunden):
    with pytest.raises(KonfigFehler):
        werte_aus_umgebung({**ENV, "MAX_GESPRAECH_SEKUNDEN": sekunden})
