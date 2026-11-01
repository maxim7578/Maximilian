import queue

import pytest

from bmw_cardata.gui.runner import Job, build_args, drain, export_csv, start_command


def _warten(job, ereignisse, sekunden=5):
    job.thread.join(sekunden)
    assert not job.thread.is_alive()
    return drain(ereignisse)


def test_befehl_läuft_im_hintergrund_und_meldet_ausgabe_und_ende():
    gesehen = []

    def ausfuehren(argv, out, err, stop):
        gesehen.append(argv)
        out.write("Hallo\n")
        err.write("Hinweis\n")
        return 0

    ereignisse = queue.Queue()
    job = start_command(["kontingent"], ereignisse, state="/tmp/x.json", run=ausfuehren)
    assert _warten(job, ereignisse) == [("out", "Hallo\n"), ("err", "Hinweis\n"), ("done", 0)]
    assert gesehen == [["--state", "/tmp/x.json", "kontingent"]]


def test_ohne_eigene_anmeldedatei_gilt_der_standard():
    ereignisse = queue.Queue()
    gesehen = []
    job = start_command(["status"], ereignisse, run=lambda argv, out, err, stop: gesehen.append(argv) or 0)
    _warten(job, ereignisse)
    assert gesehen == [["status"]]


def test_stoppen_wird_an_den_befehl_weitergegeben():
    def ausfuehren(argv, out, err, stop):
        while not stop():
            pass
        out.write("gestoppt\n")
        return 0

    ereignisse = queue.Queue()
    job = start_command(["live"], ereignisse, run=ausfuehren)
    job.stop()
    assert ("out", "gestoppt\n") in _warten(job, ereignisse)


def test_unerwarteter_fehler_wird_gemeldet_statt_die_app_zu_beenden():
    def kaputt(argv, out, err, stop):
        raise RuntimeError("geht nicht")

    ereignisse = queue.Queue()
    ereignisse_liste = _warten(start_command(["status"], ereignisse, run=kaputt), ereignisse)
    assert ereignisse_liste[-1] == ("done", 1)
    assert "RuntimeError: geht nicht" in ereignisse_liste[0][1]


def test_falsche_argumente_beenden_nur_den_befehl():
    def argparse_fehler(argv, out, err, stop):
        raise SystemExit(2)

    ereignisse = queue.Queue()
    assert _warten(start_command(["x"], ereignisse, run=argparse_fehler), ereignisse)[-1] == ("done", 2)


def test_job_meldet_ob_er_läuft():
    ereignisse = queue.Queue()
    job = start_command(["kontingent"], ereignisse, run=lambda argv, out, err, stop: 0)
    _warten(job, ereignisse)
    assert isinstance(job, Job) and not job.running


@pytest.mark.parametrize("befehl, optionen, erwartet", [
    ("status", {"vin": "WBA12345678901234"}, ["status", "WBA12345678901234"]),
    ("status", {"vin": "  ", "speichern": True}, ["status", "--speichern"]),
    ("live", {"vin": "", "speichern": True}, ["live", "--speichern"]),
    ("anmelden", {"client_id": " abc-123 ", "nur_api": True}, ["anmelden", "--client-id", "abc-123", "--nur-api"]),
    ("anmelden", {"client_id": ""}, ["anmelden"]),
    ("verlauf", {"anzahl": 25}, ["verlauf", "--anzahl", "25"]),
    ("basisdaten", {"vin": "wba12345678901234"}, ["basisdaten", "wba12345678901234"]),
    ("fahrzeuge", {}, ["fahrzeuge"]),
    ("live", {"warnungen": True}, ["live", "--warnungen"]),
    ("warnungen-pruefen", {"vin": "WBA12345678901234"}, ["warnungen", "pruefen", "WBA12345678901234"]),
    ("warnungen-test", {}, ["warnungen", "test"]),
    ("warnungen-einstellen", {"einstellungen": {"ntfy_thema": " neu ", "ladestand": "", "batterie_12v": "45,5"}},
     ["warnungen", "einstellen", "--ntfy-thema", "neu", "--batterie-12v", "45.5"]),
])
def test_argumente_werden_aus_den_eingaben_gebaut(befehl, optionen, erwartet):
    assert build_args(befehl, **optionen) == erwartet


def test_basisdaten_ohne_fahrgestellnummer_ist_ein_fehler():
    with pytest.raises(ValueError, match="Fahrgestellnummer"):
        build_args("basisdaten", vin="")


def test_csv_export_schreibt_mit_bom_für_excel(tmp_path):
    def ausfuehren(argv, out, err, stop):
        assert argv[-2:] == ["verlauf", "--csv"]
        out.write("zeit;Kilometerstand\n2026-10-31;42000\n")
        return 0

    ziel = tmp_path / "fahrten.csv"
    assert export_csv(ziel, state=str(tmp_path / "s.json"), run=ausfuehren) == (0, "")
    assert ziel.read_bytes().startswith(b"\xef\xbb\xbfzeit;Kilometerstand")


def test_csv_export_meldet_fehler_ohne_datei(tmp_path):
    def kaputt(argv, out, err, stop):
        err.write("Dateifehler\n")
        return 1

    ziel = tmp_path / "fahrten.csv"
    assert export_csv(ziel, run=kaputt) == (1, "Dateifehler\n")
    assert not ziel.exists()


def test_echte_kommandozeile_wird_aufgerufen(tmp_path):
    ereignisse = queue.Queue()
    job = start_command(["kontingent"], ereignisse, state=str(tmp_path / "s.json"))
    ausgabe = "".join(str(text) for art, text in _warten(job, ereignisse) if art == "out")
    assert "0 von 50" in ausgabe
