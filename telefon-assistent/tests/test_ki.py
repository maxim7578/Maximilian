import json

from assistent.ki import Auftrag


def test_anruf_vollstaendig():
    a = Auftrag.aus_json(json.dumps({
        "typ": "anruf", "ziel": "Da Mario", "ort": "Köln",
        "auftrag": "Tisch für 2 am Freitag um 17 Uhr reservieren", "spielraum": None,
    }))
    assert a.typ == "anruf" and a.ziel == "Da Mario" and a.spielraum == ""


def test_anruf_ohne_ziel_wird_rueckfrage():
    a = Auftrag.aus_json(json.dumps({"typ": "anruf", "auftrag": "Tisch reservieren"}))
    assert a.typ == "rueckfrage" and a.rueckfrage


def test_anruf_ohne_auftrag_wird_rueckfrage():
    a = Auftrag.aus_json(json.dumps({"typ": "anruf", "ziel": "Da Mario"}))
    assert a.typ == "rueckfrage"


def test_kaputtes_json():
    assert Auftrag.aus_json("kein json").typ == "sonstiges"
    assert Auftrag.aus_json("[1, 2]").typ == "sonstiges"


def test_unbekannter_typ():
    a = Auftrag.aus_json(json.dumps({"typ": "pizza"}))
    assert a.typ == "sonstiges" and a.antwort
