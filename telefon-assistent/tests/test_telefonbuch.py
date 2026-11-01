import pytest

from assistent.telefonbuch import Kontakte, NummernFehler, normalisieren, pruefen


@pytest.mark.parametrize(
    "eingabe, erwartet",
    [
        ("+49 (30) 123-456", "030123456"),
        ("0049 221 98765", "022198765"),
        ("0221 / 98 76 5", "022198765"),
        ("+43 1 234567", "00431234567"),
        ("0171 1234567", "01711234567"),
    ],
)
def test_normalisieren(eingabe, erwartet):
    assert normalisieren(eingabe) == erwartet


@pytest.mark.parametrize("nummer", ["110", "112", "0900 123456", "0137 123", "11833", "0180 5 123", "+43 1 234567"])
def test_gesperrte_nummern(nummer):
    with pytest.raises(NummernFehler):
        pruefen(nummer)


@pytest.mark.parametrize(
    "nummer",
    [
        "01088 0043 1 234567",  # Call-by-Call ins Ausland
        "01088 0900 1234567",  # Call-by-Call auf Mehrwertdienst
        "010 12 030 123456",  # Call-by-Call mit kurzer Vorwahl
        "0123 4567890",  # innovative Dienste
        "0181 1234567",  # internationale virtuelle Netze
        "0189 12345",
        "0191 12345",  # Online-Dienste
        "0194 12345",
        "0131 12345",  # nicht vergebener Bereich
    ],
)
def test_teure_vorwahlen_gesperrt(nummer):
    with pytest.raises(NummernFehler):
        pruefen(nummer)


@pytest.mark.parametrize(
    "nummer, erwartet",
    [
        ("030 123456", "030123456"),
        ("0221 98765", "022198765"),
        ("0171 1234567", "01711234567"),
        ("0151 12345678", "015112345678"),
        ("0160 1234567", "01601234567"),
        ("0800 1234567", "08001234567"),
        ("234567", "234567"),  # Ortsnummer ohne Vorwahl
    ],
)
def test_normale_nummern_erlaubt(nummer, erwartet):
    assert pruefen(nummer) == erwartet


@pytest.mark.parametrize("nummer", ["abc", "", "12"])
def test_ungueltige_nummern(nummer):
    with pytest.raises(NummernFehler):
        normalisieren(nummer)


def test_kontakte(tmp_path):
    kontakte = Kontakte(tmp_path / "kontakte.json")
    assert kontakte.suchen("Da Mario") is None
    assert kontakte.speichern("Da Mario", "+49 221 123456") == "0221123456"
    treffer = kontakte.suchen("da mario")
    assert treffer and treffer.nummer == "0221123456"
    with pytest.raises(NummernFehler):
        kontakte.speichern("Notruf", "112")
