from datetime import datetime

from assistent import texte

JETZT = datetime(2026, 10, 16, 14, 30)


def test_ki_offenlegung_in_beiden_richtungen():
    raus = texte.gespraech_raus("Herrn Koch", "Da Mario", "Tisch reservieren", "", "", JETZT)
    rein = texte.gespraech_rein("Herrn Koch", JETZT)
    for text in (raus, rein):
        assert "KI" in text and "gespraech_beenden" in text


def test_datum_im_befehlstext():
    text = texte.befehl_verstehen("Herrn Koch", "Köln", JETZT)
    assert "Freitag, 16.10.2026, 14:30 Uhr" in text


def test_rueckrufnummer_nur_wenn_gesetzt():
    ohne = texte.gespraech_raus("Herrn Koch", "X", "Y", "", "", JETZT)
    mit = texte.gespraech_raus("Herrn Koch", "X", "Y", "", "0221 1", JETZT)
    assert "Gib keine Telefonnummer heraus" in ohne and "0221 1" in mit


def test_begruessung_vorab():
    gruss = texte.begruessung_raus("Herrn Koch", "Katja", True)
    assert gruss == "Hallo, guten Tag!" and "Katja" not in gruss
    raus = texte.gespraech_raus("Herrn Koch", "X", "Y", "", "", JETZT, "Katja", True, gruss)
    assert gruss in raus and "Wiederhole das nicht" in raus and "Ich bin eine KI-Assistentin" in raus
    rein = texte.gespraech_rein("Herrn Koch", JETZT, "Florian", False, texte.begruessung_rein())
    assert "Sie sprechen mit dem KI-Assistenten von Herrn Koch" in rein
