"""Sicherheitsvoreinstellungen des Backend Managers (Befund aus docs/sicherheitspruefung-2026-11-01.md)."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# app.config legt beim Import Settings() an; ohne APP_ENV gilt Produktion und verlangt einen Schlüssel.
os.environ.setdefault("APP_ENV", "test")

from app.config import DEFAULT_JWT_SECRET, Settings  # noqa: E402

GEHEIM = "a" * 64


def test_ohne_app_env_gilt_produktion(monkeypatch):
    """Wer APP_ENV vergisst, bekommt die sicheren Produktionsregeln, nicht Mock-OTP und Standardschlüssel."""
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None)


def test_entwicklung_behaelt_bequeme_voreinstellungen(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    s = Settings(_env_file=None)
    assert s.APP_ENV == "development"
    assert s.DEV_MOCK_OTP == "123456"
    assert s.CORS_ORIGINS == []


def test_produktion_ohne_eigenen_jwt_schluessel_startet_nicht():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, APP_ENV="production")
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, APP_ENV="production", JWT_SECRET_KEY=DEFAULT_JWT_SECRET)


def test_produktion_schaltet_mock_otp_und_debug_ab():
    s = Settings(_env_file=None, APP_ENV="production", JWT_SECRET_KEY=GEHEIM)
    assert s.DEV_MOCK_OTP == ""
    assert s.DEBUG is False


def test_produktion_lehnt_ausdruecklichen_mock_otp_ab():
    with pytest.raises(ValueError, match="DEV_MOCK_OTP"):
        Settings(_env_file=None, APP_ENV="production", JWT_SECRET_KEY=GEHEIM, DEV_MOCK_OTP="123456")


def test_produktion_lehnt_zu_kurzen_schluessel_ab():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, APP_ENV="production", JWT_SECRET_KEY="kurz")


def test_cors_nur_fuer_ausdruecklich_erlaubte_urspruenge():
    s = Settings(_env_file=None, APP_ENV="development", CORS_ORIGINS=["https://playground.example"])
    assert s.CORS_ORIGINS == ["https://playground.example"]
