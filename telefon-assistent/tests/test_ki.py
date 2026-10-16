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


def test_gestreamte_antwort_satzweise_und_werkzeug():
    import asyncio

    import httpx

    from assistent.ki import KI

    ereignisse = [
        {"choices": [{"delta": {"content": "Okay. Für wie"}}]},
        {"choices": [{"delta": {"content": " viele Personen?"}}]},
        {"choices": [{"delta": {"content": " Danke"}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "t1", "function": {
            "name": "gespraech_beenden", "arguments": '{"ergebnis": "ok",'}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ' "erfolgreich": true}'}}]}}]},
    ]
    rumpf = "".join(f"data: {json.dumps(e)}\n\n" for e in ereignisse) + "data: [DONE]\n\n"

    def antworten(anfrage):
        assert json.loads(anfrage.content)["stream"] is True
        return httpx.Response(200, text=rumpf, headers={"content-type": "text/event-stream"})

    async def ablauf():
        ki = KI("k", "openai/gpt-oss-120b", "w", "Herrn Koch", "")
        ki._client = httpx.AsyncClient(base_url="https://x", transport=httpx.MockTransport(antworten))
        saetze = []

        async def bei_satz(satz):
            saetze.append(satz)

        antwort = await ki.gespraech_antwort_strom([], [], bei_satz)
        return saetze, antwort

    saetze, antwort = asyncio.run(ablauf())
    assert saetze == ["Okay.", "Für wie viele Personen?", "Danke"]
    assert antwort.werkzeug == "gespraech_beenden" and antwort.argumente == {"ergebnis": "ok", "erfolgreich": True}
    assert antwort.roh["tool_calls"][0]["id"] == "t1"
