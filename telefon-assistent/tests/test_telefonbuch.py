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
