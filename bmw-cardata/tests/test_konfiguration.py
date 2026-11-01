from pathlib import Path

import pytest

from bmw_cardata.config import (
    CLIENT_ID_ENV,
    DEFAULT_HISTORY_DAYS,
    HISTORY_DAYS_ENV,
    NO_LOCATION_ENV,
    STATE_PATH_ENV,
    ConfigError,
    client_id_from_env,
    history_days,
    location_disabled,
    parse_history_days,
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


def test_aufbewahrungsfrist_hat_einen_standard_von_einem_jahr():
    assert DEFAULT_HISTORY_DAYS == 365
    assert history_days(None, {}) == 365


def test_aufbewahrungsfrist_aus_umgebungsvariable_und_option_hat_vorrang():
    assert history_days(None, {HISTORY_DAYS_ENV: " 30 "}) == 30
    assert history_days(7, {HISTORY_DAYS_ENV: "30"}) == 7
    assert history_days(0, {}) == 0


@pytest.mark.parametrize("ungueltig", ["", "abc", "-1", "3651", "1.5"])
def test_ungueltige_aufbewahrungsfrist_nennt_die_umgebungsvariable(ungueltig):
    with pytest.raises(ConfigError, match=HISTORY_DAYS_ENV):
        history_days(None, {HISTORY_DAYS_ENV: ungueltig})


@pytest.mark.parametrize("ungueltig", ["abc", "-1", "3651"])
def test_ungueltige_aufbewahrungsfrist_wird_abgelehnt(ungueltig):
    with pytest.raises(ConfigError):
        parse_history_days(ungueltig)


@pytest.mark.parametrize("wert", ["1", "ja", "JA", "true", "yes", "on"])
def test_standort_weglassen_per_umgebungsvariable(wert):
    assert location_disabled(False, {NO_LOCATION_ENV: wert}) is True


@pytest.mark.parametrize("wert", ["", "0", "nein", "false"])
def test_standort_wird_ohne_einstellung_gespeichert(wert):
    assert location_disabled(False, {NO_LOCATION_ENV: wert}) is False
    assert location_disabled(False, {}) is False


def test_option_ohne_standort_gilt_auch_ohne_umgebungsvariable():
    assert location_disabled(True, {}) is True
