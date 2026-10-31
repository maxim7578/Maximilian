import pytest

from bmw_cardata.alerts import (
    Alert,
    AlertSettings,
    charging_status,
    evaluate,
    is_charging,
    new_alerts,
)

SOC = "vehicle.drivetrain.batteryManagement.header"
V12 = "vehicle.electricalSystem.battery.stateOfCharge"
SCHLOSS = "vehicle.cabin.door.lock.status"
FAHRERTUER = "vehicle.cabin.door.row1.driver.isOpen"
FENSTER = "vehicle.cabin.window.row2.passenger.status"
DACH = "vehicle.cabin.sunroof.status"
HECK = "vehicle.body.trunk.isOpen"
HAUBE = "vehicle.body.hood.isOpen"
DRUCK_VL = "vehicle.chassis.axle.row1.wheel.left.tire.pressure"
SOLL_VL = "vehicle.chassis.axle.row1.wheel.left.tire.pressureTarget"
LADEN = "vehicle.drivetrain.electricEngine.charging.status"


def w(value, unit=None):
    return {"value": value, **({"unit": unit} if unit else {})}


def _schluessel(daten, einstellungen=AlertSettings()):
    return [a.key for a in evaluate(daten, einstellungen)]


def test_alles_in_ordnung_ergibt_keine_warnung():
    daten = {SCHLOSS: w("SECURED"), FAHRERTUER: w(False), FENSTER: w("CLOSED"), SOC: w(80, "%"),
             V12: w(90, "%"), DRUCK_VL: w(250, "kPa"), SOLL_VL: w(250, "kPa"), HECK: w(False)}
    assert evaluate(daten, AlertSettings()) == ()


def test_offene_tür_klappen_und_fenster():
    daten = {FAHRERTUER: w(True), FENSTER: w("INTERMEDIATE"), DACH: w("OPEN"), HECK: w("true"), HAUBE: w(True)}
    texte = [a.text for a in evaluate(daten, AlertSettings())]
    assert texte == [
        "Fahrertür offen",
        "Fenster hinten Beifahrerseite: teilweise offen",
        "Heckklappe offen",
        "Motorhaube offen",
        "Schiebedach: offen",
    ]


def test_nicht_verriegelt_nennt_den_originalwert():
    alarme = evaluate({SCHLOSS: w("SELECTIVE_LOCKED")}, AlertSettings())
    assert alarme == (Alert("nicht_verriegelt", "Nicht verriegelt (Türschloss meldet SELECTIVE_LOCKED)"),)
    assert evaluate({SCHLOSS: w("locked")}, AlertSettings()) == ()


def test_verriegelt_werte_sind_einstellbar():
    einstellungen = AlertSettings(locked_values=("SELECTIVE_LOCKED",))
    assert evaluate({SCHLOSS: w("SELECTIVE_LOCKED")}, einstellungen) == ()
    assert _schluessel({SCHLOSS: w("SECURED")}, einstellungen) == ["nicht_verriegelt"]


def test_ladestand_und_12v_unter_der_grenze():
    daten = {SOC: w(15, "%"), V12: w(40, "%")}
    assert evaluate(daten, AlertSettings()) == (
        Alert("ladestand_niedrig", "Ladestand niedrig: 15 % (Grenze 20 %)"),
        Alert("batterie_12v_niedrig", "12-V-Batterie schwach: 40 % (Grenze 50 %)"),
    )
    assert evaluate(daten, AlertSettings(min_soc=10, min_12v=30)) == ()


def test_reifendruck_unter_dem_solldruck():
    daten = {DRUCK_VL: w(225, "kPa"), SOLL_VL: w(250, "kPa")}
    assert evaluate(daten, AlertSettings()) == (
        Alert("reifendruck:vorne links", "Reifendruck vorne links: 2.25 bar, Soll 2.50 bar"),
    )
    assert evaluate(daten, AlertSettings(tire_tolerance_bar=0.3)) == ()


def test_reifendruck_ohne_solldruck_oder_mit_anderer_einheit_wird_nicht_bewertet():
    assert evaluate({DRUCK_VL: w(100, "kPa")}, AlertSettings()) == ()
    assert evaluate({DRUCK_VL: w(1.0, "bar"), SOLL_VL: w(2.5, "bar")}, AlertSettings()) == ()
    assert evaluate({DRUCK_VL: w("INVALID", "kPa"), SOLL_VL: w(250, "kPa")}, AlertSettings()) == ()


@pytest.mark.parametrize("wert", ["unbekannt", None, True, "nan"])
def test_unbrauchbare_zahlen_lösen_nichts_aus(wert):
    assert evaluate({SOC: w(wert, "%"), V12: w(wert, "%")}, AlertSettings()) == ()


def test_ladestatus_und_ob_geladen_wird():
    assert charging_status({LADEN: w("chargingactive")}) == "CHARGINGACTIVE"
    assert charging_status({}) is None
    assert is_charging("CHARGINGACTIVE") and is_charging("CHARGING_IN_PROGRESS")
    assert not is_charging("NOCHARGING") and not is_charging(None)


def test_neue_warnungen_nur_einmal():
    alt = {"aktiv": ["ladestand_niedrig"]}
    jetzt = (Alert("ladestand_niedrig", "x"), Alert("heckklappe", "Heckklappe offen"))
    assert new_alerts(jetzt, alt, None) == [Alert("heckklappe", "Heckklappe offen")]
    assert new_alerts(jetzt, {}, None) == list(jetzt)


def test_laden_beendet_ist_ein_ereignis_beim_wechsel():
    alt = {"ladestatus": "CHARGINGACTIVE"}
    assert new_alerts((), alt, "NOCHARGING") == [Alert("laden_beendet", "Laden beendet (NOCHARGING)")]
    assert new_alerts((), alt, "CHARGINGACTIVE") == []
    assert new_alerts((), alt, None) == []
    assert new_alerts((), {"ladestatus": "NOCHARGING"}, "NOCHARGING") == []


def test_einstellungen_werden_geprüft():
    with pytest.raises(ValueError, match="https"):
        AlertSettings(ntfy_server="http://ntfy.sh")
    with pytest.raises(ValueError, match="Thema"):
        AlertSettings(ntfy_topic="mit leerzeichen")
    with pytest.raises(ValueError, match="Ladestand"):
        AlertSettings(min_soc=150)
    with pytest.raises(ValueError, match="Toleranz"):
        AlertSettings(tire_tolerance_bar=-1)
    assert AlertSettings(ntfy_topic="bmw-abc_123").ntfy_topic == "bmw-abc_123"


def test_warnungen_ohne_neue_daten_bleiben_aktiv():
    from bmw_cardata.alerts import carried_over

    alt = ["offen:Fenster Fahrer", "ladestand_niedrig", "reifendruck:vorne links", "nicht_verriegelt", "unbekannt"]
    assert carried_over(alt, {SOC: w(80, "%")}) == [
        "offen:Fenster Fahrer", "reifendruck:vorne links", "nicht_verriegelt"]
    # Nur der Solldruck reicht nicht, um die Reifenwarnung zu beurteilen: Sie bleibt aktiv.
    assert carried_over(alt, {SOLL_VL: w(250, "kPa"), SCHLOSS: w("LOCKED")}) == [
        "offen:Fenster Fahrer", "ladestand_niedrig", "reifendruck:vorne links"]


def test_unbekannte_öffnung_im_zustand_wird_verworfen():
    from bmw_cardata.alerts import carried_over

    assert carried_over(["offen:gibt es nicht"], {}) == []


def test_reifenwarnung_bleibt_wenn_nur_der_druck_kommt():
    from bmw_cardata.alerts import carried_over

    assert carried_over(["reifendruck:vorne links"], {DRUCK_VL: w(230, "kPa")}) == ["reifendruck:vorne links"]
    assert carried_over(["reifendruck:vorne links"], {DRUCK_VL: w(250, "kPa"), SOLL_VL: w(250, "kPa")}) == []


@pytest.mark.parametrize("daten", [{SCHLOSS: w("INVALID")}, {SOC: w("INVALID", "%")}, {FENSTER: w("INVALID")}])
def test_ungültige_werte_beenden_keine_warnung(daten):
    from bmw_cardata.alerts import carried_over

    alt = ["nicht_verriegelt", "ladestand_niedrig", "offen:Fenster hinten Beifahrerseite"]
    assert len(carried_over(alt, daten)) == 3


def test_ungültiges_türschloss_ist_kein_alarm():
    assert evaluate({SCHLOSS: w("INVALID")}, AlertSettings()) == ()
    assert evaluate({SCHLOSS: w(" ")}, AlertSettings()) == ()


@pytest.mark.parametrize("neu", ["INVALID", "UNKNOWN", "", "CHARGINGPAUSED", "CHARGING_PAUSED"])
def test_pause_und_ungültig_sind_kein_ladeende(neu):
    assert charging_status({LADEN: w(neu)}) in (None, "CHARGINGPAUSED", "CHARGING_PAUSED")
    assert new_alerts((), {"ladestatus": "CHARGINGACTIVE"}, charging_status({LADEN: w(neu)})) == []


def test_server_adresse_wird_geprüft():
    for adresse in ("https://", "https://[::1", "https:// leer.example"):
        with pytest.raises(ValueError, match="https"):
            AlertSettings(ntfy_server=adresse)
    assert AlertSettings(ntfy_server="https://push.example:8443/").ntfy_server == "https://push.example:8443/"


def test_unbekannte_reifenposition_im_zustand_wird_verworfen():
    from bmw_cardata.alerts import carried_over

    assert carried_over(["reifendruck:mitte"], {}) == []
