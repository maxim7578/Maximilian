import json
import stat

import pytest

from bmw_cardata.state import StateError, delete_state, load_state, save_state


def test_gespeicherter_zustand_wird_unverändert_geladen(tmp_path, make_state):
    pfad = tmp_path / "unter" / "state.json"
    zustand = make_state(container_id="behaelter-1")
    save_state(pfad, zustand)
    assert load_state(pfad) == zustand


def test_datei_ist_nur_für_den_eigenen_benutzer_lesbar(tmp_path, make_state):
    pfad = tmp_path / "state.json"
    save_state(pfad, make_state())
    assert stat.S_IMODE(pfad.stat().st_mode) == 0o600
    assert not (tmp_path / "state.json.tmp").exists()


def test_fehlende_datei_fordert_anmeldung(tmp_path):
    with pytest.raises(StateError, match="anmelden"):
        load_state(tmp_path / "fehlt.json")


@pytest.mark.parametrize("inhalt", ["kein json", json.dumps({"client_id": "x"}), json.dumps([1, 2])])
def test_beschädigte_datei_wird_erkannt(tmp_path, inhalt):
    pfad = tmp_path / "state.json"
    pfad.write_text(inhalt)
    with pytest.raises(StateError, match="beschädigt"):
        load_state(pfad)


def test_zustand_ist_unveränderlich_und_kopien_ändern_das_original_nicht(make_state):
    original = make_state()
    kopie = original.with_container("neu")
    assert original.container_id is None
    assert kopie.container_id == "neu"
    with pytest.raises(AttributeError):
        original.client_id = "anders"


def test_abmelden_löscht_die_datei_und_meldet_ob_etwas_da_war(tmp_path, make_state):
    pfad = tmp_path / "state.json"
    save_state(pfad, make_state())
    assert delete_state(pfad) is True
    assert delete_state(pfad) is False


def test_fahrgestellnummer_wird_mitgespeichert(tmp_path, make_state):
    pfad = tmp_path / "state.json"
    zustand = make_state().with_vin("WBA12345678901234")
    save_state(pfad, zustand)
    assert load_state(pfad).vin == "WBA12345678901234"


def test_ältere_datei_ohne_fahrgestellnummer_bleibt_lesbar(tmp_path, make_state):
    pfad = tmp_path / "state.json"
    save_state(pfad, make_state())
    roh = json.loads(pfad.read_text())
    del roh["vin"]
    pfad.write_text(json.dumps(roh))
    assert load_state(pfad).vin is None
