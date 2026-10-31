import base64
import hashlib

import pytest

from bmw_cardata.auth import (
    DEVICE_GRANT,
    AuthError,
    DeviceCode,
    Tokens,
    create_pkce_pair,
    poll_for_tokens,
    refresh_tokens,
    request_device_code,
)

DEVICE_PATH = "/gcdm/oauth/device/code"
TOKEN_PATH = "/gcdm/oauth/token"
TOKEN_ANTWORT = {"access_token": "zugang", "refresh_token": "erneuerung", "expires_in": 3599, "scope": "s"}


def _geraet(expires_in=900, interval=5):
    return DeviceCode("geraet-1", "ABCD-EFGH", "https://bmw.example/geraet", "", expires_in, interval)


class Uhr:
    def __init__(self):
        self.jetzt = 0.0
        self.pausen = []

    def sleep(self, sekunden):
        self.pausen.append(sekunden)
        self.jetzt += sekunden


def test_pkce_challenge_ist_sha256_des_verifiers_ohne_auffuellzeichen():
    verifier, challenge = create_pkce_pair()
    erwartet = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == erwartet
    assert 43 <= len(verifier) <= 128
    assert "=" not in challenge


def test_gerätecode_anfrage_sendet_pkce_und_scope(bmw):
    bmw.add("POST", DEVICE_PATH, body={
        "device_code": "geraet-1", "user_code": "ABCD", "verification_uri": "https://v",
        "verification_uri_complete": "https://v?c=ABCD", "expires_in": 600, "interval": 3,
    })
    geraet = request_device_code(bmw.client(), "client-1234", "challenge-x")
    formular = bmw.form(0)
    assert formular["code_challenge"] == "challenge-x"
    assert formular["code_challenge_method"] == "S256"
    assert formular["response_type"] == "device_code"
    assert "cardata:api:read" in formular["scope"]
    assert geraet == DeviceCode("geraet-1", "ABCD", "https://v", "https://v?c=ABCD", 600, 3)


def test_abgelehnter_gerätecode_meldet_status_ohne_tokens(bmw):
    bmw.add("POST", DEVICE_PATH, status=400, body={"error": "invalid_client", "access_token": "geheim"})
    with pytest.raises(AuthError) as fehler:
        request_device_code(bmw.client(), "client-1234", "c")
    assert "400" in str(fehler.value)
    assert "geheim" not in str(fehler.value)


def test_unvollständige_gerätecode_antwort_ist_ein_fehler(bmw):
    bmw.add("POST", DEVICE_PATH, body={"user_code": "ABCD"})
    with pytest.raises(AuthError, match="unvollständig"):
        request_device_code(bmw.client(), "client-1234", "c")


def test_abfrage_wartet_bis_zur_bestätigung(bmw):
    uhr = Uhr()
    bmw.add("POST", TOKEN_PATH, status=400, body={"error": "authorization_pending"})
    bmw.add("POST", TOKEN_PATH, status=400, body={"error": "slow_down"})
    bmw.add("POST", TOKEN_PATH, body=TOKEN_ANTWORT)
    tokens = poll_for_tokens(bmw.client(), "client-1234", _geraet(), "verifier-x",
                             sleep=uhr.sleep, clock=lambda: uhr.jetzt, wall_clock=lambda: 1000.0)
    assert tokens == Tokens("zugang", "erneuerung", 4599.0, "s")
    assert uhr.pausen == [5, 10]
    formular = bmw.form(0)
    assert formular["grant_type"] == DEVICE_GRANT
    assert formular["code_verifier"] == "verifier-x"


def test_abgelehnte_bestätigung_bricht_sofort_ab(bmw):
    bmw.add("POST", TOKEN_PATH, status=400, body={"error": "access_denied", "refresh_token": "geheim"})
    with pytest.raises(AuthError) as fehler:
        poll_for_tokens(bmw.client(), "client-1234", _geraet(), "v", sleep=lambda s: None)
    assert "access_denied" in str(fehler.value)
    assert "geheim" not in str(fehler.value)


def test_abfrage_endet_nach_ablauf_des_gerätecodes(bmw):
    uhr = Uhr()
    bmw.add("POST", TOKEN_PATH, status=400, body={"error": "authorization_pending"})
    with pytest.raises(AuthError, match="Zeit abgelaufen"):
        poll_for_tokens(bmw.client(), "client-1234", _geraet(expires_in=12, interval=5), "v",
                        sleep=uhr.sleep, clock=lambda: uhr.jetzt)
    assert len(bmw.requests) == 3


def test_antwort_ohne_json_gilt_als_fehler(bmw):
    bmw.add("POST", TOKEN_PATH, status=500, raw=b"<html>Fehler</html>")
    with pytest.raises(AuthError, match="500"):
        poll_for_tokens(bmw.client(), "client-1234", _geraet(), "v", sleep=lambda s: None)


def test_erneuerung_behält_alten_refresh_token_wenn_keiner_kommt(bmw):
    bmw.add("POST", TOKEN_PATH, body={"access_token": "neu", "expires_in": 100})
    alt = Tokens("alt", "erneuerung-alt", 0.0)
    neu = refresh_tokens(bmw.client(), "client-1234", alt, now=50.0)
    assert neu == Tokens("neu", "erneuerung-alt", 150.0, "")
    assert bmw.form(0)["grant_type"] == "refresh_token"
    assert bmw.form(0)["refresh_token"] == "erneuerung-alt"


def test_fehlgeschlagene_erneuerung_fordert_neue_anmeldung(bmw):
    bmw.add("POST", TOKEN_PATH, status=401, body={"error": "invalid_grant"})
    with pytest.raises(AuthError, match="anmelden"):
        refresh_tokens(bmw.client(), "client-1234", Tokens("a", "r", 0.0), now=0.0)


def test_token_ohne_zugangstoken_ist_ungültig():
    with pytest.raises(AuthError):
        Tokens.from_response({"refresh_token": "r"}, now=0.0)


def test_fehlende_laufzeit_bedeutet_eine_stunde():
    assert Tokens.from_response({"access_token": "a", "refresh_token": "r"}, now=10.0).expires_at == 3610.0


def test_token_gilt_kurz_vor_ablauf_schon_als_abgelaufen():
    tokens = Tokens("a", "r", expires_at=1000.0)
    assert not tokens.is_expired(now=900.0)
    assert tokens.is_expired(now=950.0)
