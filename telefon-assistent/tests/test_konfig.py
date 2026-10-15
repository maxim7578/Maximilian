from pathlib import Path

import pytest

from assistent.konfig import KonfigFehler, erzeugen, werte_aus_umgebung

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
