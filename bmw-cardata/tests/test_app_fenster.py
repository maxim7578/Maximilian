import gc
import time
import tkinter as tk

import pytest

from bmw_cardata.gui.app import App


@pytest.fixture
def fenster():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Keine Anzeige vorhanden (z. B. ohne Xvfb)")
    root.withdraw()
    yield root
    root.destroy()
    # tkinter-Variablen im Haupt-Thread aufräumen: Räumt sie später ein Hintergrund-Thread
    # auf, bricht Tcl mit "Tcl_AsyncDelete: async handler deleted by the wrong thread" ab.
    gc.collect()


class Befehle:
    """Nachgebaute Kommandozeile: merkt sich Aufrufe und antwortet fest."""

    def __init__(self, antwort="", fehler="", code=0):
        self.aufrufe, self.antwort, self.fehler, self.code = [], antwort, fehler, code

    def __call__(self, argv, out, err, stop):
        self.aufrufe.append(argv)
        if argv[-1] == "live" or "live" in argv:
            while not stop():
                time.sleep(0.01)
            out.write("live beendet\n")
            return 0
        out.write(self.antwort)
        err.write(self.fehler)
        return self.code


def _bis_fertig(app, root, sekunden=5):
    ende = time.time() + sekunden
    while time.time() < ende:
        root.update()
        if not (app.job and app.job.running) and app.events.empty():
            root.update()
            return
        time.sleep(0.01)
    raise AssertionError("Befehl wurde nicht fertig")


def _knopf(app, text):
    return next(b for b in [*app.buttons, app.stop_button] if b.cget("text") == text)


def test_fenster_hat_alle_funktionen(fenster):
    app = App(fenster, run=Befehle())
    texte = {b.cget("text") for b in app.buttons} | {app.stop_button.cget("text")}
    assert texte == {"Anmelden", "Abmelden", "Fahrzeuge", "Status", "Status speichern", "Basisdaten",
                     "Kontingent", "Warnungen prüfen", "Warnungen einstellen …", "Live starten", "Live stoppen",
                     "Anzeigen", "Als CSV speichern …"}
    assert fenster.title().startswith("BMW CarData")


def test_status_knopf_zeigt_die_ausgabe(fenster):
    befehle = Befehle(antwort="Fahrzeug WBA12345678901234\n  Kilometerstand: 42063 km\n")
    app = App(fenster, state="/tmp/s.json", run=befehle)
    app.vin.set("WBA12345678901234")
    _knopf(app, "Status").invoke()
    _bis_fertig(app, fenster)
    assert befehle.aufrufe == [["--state", "/tmp/s.json", "status", "WBA12345678901234"]]
    assert "Kilometerstand: 42063 km" in app.text()
    assert app.status.get() == "Fertig."


def test_fehler_erscheinen_und_knöpfe_werden_wieder_frei(fenster):
    app = App(fenster, run=Befehle(fehler="Fehler: Nicht angemeldet.\n", code=1))
    _knopf(app, "Fahrzeuge").invoke()
    assert str(_knopf(app, "Status").cget("state")) == "disabled"
    _bis_fertig(app, fenster)
    assert "Nicht angemeldet" in app.text()
    assert "Code 1" in app.status.get()
    assert str(_knopf(app, "Status").cget("state")) == "normal"


def test_anmelden_übergibt_client_id_und_nur_api(fenster):
    befehle = Befehle(antwort="Öffne https://bmw.example/geraet?code=AB und bestätige.\n")
    app = App(fenster, run=befehle)
    app.client_id.set("client-1234")
    app.nur_api.set(True)
    _knopf(app, "Anmelden").invoke()
    _bis_fertig(app, fenster)
    assert befehle.aufrufe == [["anmelden", "--client-id", "client-1234", "--nur-api"]]
    links = app.output.tag_ranges("link")
    assert app.output.get(links[0], links[1]) == "https://bmw.example/geraet?code=AB"


def test_link_öffnet_den_browser(fenster):
    geoeffnet = []
    app = App(fenster, run=Befehle(), open_link=geoeffnet.append)
    app.append("Öffne https://bmw.example/x jetzt\n")
    fenster.deiconify()
    fenster.update()
    start = app.output.tag_ranges("link")[0]
    x, y, _, _ = app.output.bbox(start)

    class Klick:
        pass

    klick = Klick()
    klick.x, klick.y = x + 2, y + 2
    app._click_link(klick)
    assert geoeffnet == ["https://bmw.example/x"]


def test_live_lässt_sich_stoppen(fenster):
    app = App(fenster, run=Befehle())
    app.live_speichern.set(True)
    _knopf(app, "Live starten").invoke()
    fenster.update()
    assert str(app.stop_button.cget("state")) == "normal"
    app.stop()
    _bis_fertig(app, fenster)
    assert "live beendet" in app.text()
    assert str(app.stop_button.cget("state")) == "disabled"


def test_basisdaten_ohne_fahrgestellnummer_gibt_einen_hinweis(fenster):
    befehle = Befehle()
    app = App(fenster, run=befehle)
    _knopf(app, "Basisdaten").invoke()
    fenster.update()
    assert befehle.aufrufe == []
    assert "Fahrgestellnummer" in app.text()


def test_verlauf_mit_anzahl(fenster):
    befehle = Befehle(antwort="31.10.2026 10:00  Kilometerstand: 42063 km\n")
    app = App(fenster, run=befehle)
    app.anzahl.set(3)
    _knopf(app, "Anzeigen").invoke()
    _bis_fertig(app, fenster)
    assert befehle.aufrufe == [["verlauf", "--anzahl", "3"]]


def test_csv_speichern(fenster, tmp_path, monkeypatch):
    app = App(fenster, run=Befehle(antwort="zeit;Kilometerstand\n"))
    ziel = tmp_path / "v.csv"
    monkeypatch.setattr("bmw_cardata.gui.app.filedialog.asksaveasfilename", lambda **kw: str(ziel))
    _knopf(app, "Als CSV speichern …").invoke()
    assert ziel.read_text(encoding="utf-8-sig") == "zeit;Kilometerstand\n"
    assert "Verlauf gespeichert" in app.text()


def test_csv_abbrechen_und_fehler(fenster, tmp_path, monkeypatch):
    app = App(fenster, run=Befehle(fehler="kaputt\n", code=1))
    monkeypatch.setattr("bmw_cardata.gui.app.filedialog.asksaveasfilename", lambda **kw: "")
    app.save_csv()
    assert app.text() == ""
    app.write_csv(tmp_path / "v.csv")
    assert "kaputt" in app.text()
    app.run = Befehle(antwort="x\n")
    app.write_csv(tmp_path / "fehlt" / "v.csv")
    assert "Datei konnte nicht geschrieben werden" in app.text()


def test_ungültige_anzahl_fällt_auf_10_zurück(fenster):
    app = App(fenster, run=Befehle())
    app.anzahl.set(0)
    assert app._count() == 1
    fenster.setvar(str(app.anzahl), "abc")
    assert app._count() == 10


def test_ausgabe_leeren_und_kein_doppelstart(fenster):
    befehle = Befehle()
    app = App(fenster, run=befehle)
    _knopf(app, "Live starten").invoke()
    app._start("status")
    assert len(befehle.aufrufe) <= 1
    app.stop()
    _bis_fertig(app, fenster)
    app.clear()
    assert app.text() == ""


def test_programmstart_öffnet_das_fenster(fenster, monkeypatch):
    from bmw_cardata.gui import app as modul

    gestartet = []
    monkeypatch.setattr(modul.tk.Tk, "mainloop", lambda self: gestartet.append(self.title()))
    modul.main([])
    assert gestartet and gestartet[0].startswith("BMW CarData")


def test_selbsttest_schreibt_ok(fenster, tmp_path):
    from bmw_cardata.gui import app as modul

    bericht = tmp_path / "bericht.txt"
    with pytest.raises(SystemExit) as ende:
        modul.main(["--selbsttest", str(bericht)])
    assert ende.value.code == 0
    assert bericht.read_text(encoding="utf-8") == "OK\n"


def test_selbsttest_schreibt_den_fehler(tmp_path, monkeypatch):
    from bmw_cardata.gui import app as modul

    def kaputt():
        raise RuntimeError("kein Tcl")

    monkeypatch.setattr(modul.tk, "Tk", kaputt)
    bericht = tmp_path / "bericht.txt"
    assert modul._self_test(bericht) == 1
    assert "RuntimeError: kein Tcl" in bericht.read_text(encoding="utf-8")


def test_absturz_landet_im_protokoll(tmp_path, monkeypatch):
    from bmw_cardata.gui import app as modul

    def kaputt():
        raise RuntimeError("kein Tcl")

    gezeigt = []
    monkeypatch.setattr(modul.tk, "Tk", kaputt)
    monkeypatch.setattr(modul, "CRASH_LOG", tmp_path / "unter" / "app-fehler.log")
    monkeypatch.setattr(modul.messagebox, "showerror", lambda titel, text: gezeigt.append(text))
    with pytest.raises(SystemExit) as ende:
        modul.main([])
    assert ende.value.code == 1
    assert "RuntimeError: kein Tcl" in (tmp_path / "unter" / "app-fehler.log").read_text(encoding="utf-8")
    assert "app-fehler.log" in gezeigt[0]


def test_absturzbericht_übersteht_fehler_beim_schreiben_und_anzeigen(tmp_path, monkeypatch):
    from bmw_cardata.gui import app as modul

    def ohne_anzeige(titel, text):
        raise modul.tk.TclError("keine Anzeige")

    monkeypatch.setattr(modul.messagebox, "showerror", ohne_anzeige)
    datei = tmp_path / "datei"
    datei.write_text("")
    modul._report_crash("Fehler", datei / "app-fehler.log")


def test_warnungen_werden_hervorgehoben_und_klingeln(fenster, monkeypatch):
    app = App(fenster, run=Befehle())
    geklingelt = []
    monkeypatch.setattr(fenster, "bell", lambda: geklingelt.append(True))
    app.append("Fahrzeug X\nWarnung: Heckklappe offen\n")
    bereiche = app.output.tag_ranges("warn")
    assert app.output.get(bereiche[0], bereiche[1]) == "Warnung: Heckklappe offen\n"
    assert geklingelt == [True]
    app.append("ohne Warnung\n")
    assert geklingelt == [True]


def test_live_mit_warnungen_und_warnungen_prüfen(fenster):
    befehle = Befehle()
    app = App(fenster, run=befehle)
    _knopf(app, "Live starten").invoke()
    fenster.update()
    app.stop()
    _bis_fertig(app, fenster)
    app.vin.set("WBA12345678901234")
    _knopf(app, "Warnungen prüfen").invoke()
    _bis_fertig(app, fenster)
    assert befehle.aufrufe == [["live", "--warnungen"],
                               ["warnungen", "pruefen", "WBA12345678901234"]]


def test_einstellungsfenster_zeigt_werte_und_speichert(fenster, tmp_path):
    import json

    from bmw_cardata.gui.alert_dialog import AlertDialog

    pfad = tmp_path / "state.json"
    (tmp_path / "warnungen.json").write_text(json.dumps({"ntfy_thema": "bmw-alt", "ladestand_min": 25}))
    befehle = Befehle(antwort="Push über ntfy: https://ntfy.sh/bmw-neu\n")
    app = App(fenster, state=str(pfad), run=befehle)
    dialog = AlertDialog(fenster, str(pfad), app._start)
    assert dialog.values() == {"ntfy_thema": "bmw-alt", "ladestand": "25", "batterie_12v": "50",
                               "reifendruck_toleranz": "0.2"}
    dialog.topic.set("bmw-neu")
    dialog.tire.set("0,3")
    dialog.save()
    _bis_fertig(app, fenster)
    assert befehle.aufrufe[0] == ["--state", str(pfad), "warnungen", "einstellen", "--ntfy-thema", "bmw-neu",
                                  "--ladestand", "25.0", "--batterie-12v", "50.0", "--reifendruck-toleranz", "0.3"]
    assert "> bmw-cardata warnungen einstellen\n" in app.text()


def test_einstellungsfenster_test_push_und_neues_thema(fenster, tmp_path):
    from bmw_cardata.gui.alert_dialog import AlertDialog

    befehle = Befehle()
    app = App(fenster, state=str(tmp_path / "s.json"), run=befehle)
    _knopf(app, "Warnungen einstellen …").invoke()
    dialog = AlertDialog(fenster, str(tmp_path / "s.json"), app._start)
    dialog.test()
    _bis_fertig(app, fenster)
    assert befehle.aufrufe[-1][-2:] == ["warnungen", "test"]
    dialog.topic.set("neu")
    assert dialog.values()["ntfy_thema"] == "neu"
    dialog.window.destroy()


def test_ungültige_zahl_im_einstellungsfenster(fenster, tmp_path):
    from bmw_cardata.gui.alert_dialog import AlertDialog

    befehle = Befehle()
    app = App(fenster, state=str(tmp_path / "s.json"), run=befehle)
    dialog = AlertDialog(fenster, str(tmp_path / "s.json"), app._start)
    dialog.soc.set("viel")
    dialog.save()
    assert befehle.aufrufe == [] and "Bitte eine Zahl" in app.text()
