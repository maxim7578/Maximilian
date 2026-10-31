from pathlib import Path

import pytest

from bmw_cardata.config import (
    CLIENT_ID_ENV,
    STATE_PATH_ENV,
    ConfigError,
    client_id_from_env,
    state_path,
    validate_client_id,
    validate_vin,
)


def test_client_id_wird_von_leerzeichen_befreit():
    assert validate_client_id("  abcd-1234-efgh  ") == "abcd-1234-efgh"


@pytest.mark.parametrize("ungueltig", [None, "", "   ", "kurz", "mit leerzeichen drin", "a/b/../c-1234"])
def test_ungueltige_client_id_wird_abgelehnt(ungueltig):
    with pytest.raises(ConfigError):
        validate_client_id(ungueltig)


def test_client_id_kommt_aus_der_umgebungsvariable():
    assert client_id_from_env({CLIENT_ID_ENV: "abcd-1234-efgh"}) == "abcd-1234-efgh"


def test_fehlende_umgebungsvariable_nennt_den_variablennamen():
    with pytest.raises(ConfigError, match=CLIENT_ID_ENV):
        client_id_from_env({})


def test_fahrgestellnummer_wird_grossgeschrieben():
    assert validate_vin("wba12345678901234") == "WBA12345678901234"


@pytest.mark.parametrize("ungueltig", ["WBA123", "WBA1234567890123I", "../../containers/x", "WBA12345678901234X"])
def test_ungueltige_fahrgestellnummer_wird_abgelehnt(ungueltig):
    with pytest.raises(ConfigError):
        validate_vin(ungueltig)


def test_expliziter_pfad_hat_vorrang_vor_umgebungsvariable(tmp_path):
    assert state_path(str(tmp_path / "a.json"), {STATE_PATH_ENV: "/x/b.json"}) == tmp_path / "a.json"


def test_pfad_aus_umgebungsvariable():
    assert state_path(None, {STATE_PATH_ENV: "/x/b.json"}) == Path("/x/b.json")


def test_standardpfad_liegt_im_benutzerverzeichnis():
    assert state_path(None, {}) == Path("~/.config/bmw-cardata/state.json").expanduser()
