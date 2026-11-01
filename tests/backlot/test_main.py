"""Tests für das Backlot-CLI: Token beim Start, Weitergabe an den Server, Token-Datei (Befund N12)."""

from __future__ import annotations

import os
import stat
import sys

import pytest

from backlot import __main__ as cli
from backlot import auth as auth_mod

ENV_TOKEN = "env-token-" + "y" * 32


@pytest.fixture(autouse=True)
def token_dir(tmp_path, monkeypatch):
    directory = tmp_path / "tokens"
    monkeypatch.setattr(auth_mod, "TOKEN_DIR", directory)
    monkeypatch.delenv(auth_mod.TOKEN_ENV, raising=False)
    monkeypatch.setenv("BACKLOT_PORT", "4750")
    return directory


@pytest.fixture
def opened(monkeypatch):
    urls: list[str] = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: urls.append(url))
    return urls


@pytest.fixture
def spawned(monkeypatch):
    """Fängt den Serverstart ab; danach meldet die Health-Prüfung den Server als bereit."""
    calls: list[dict] = []
    alive = {"value": False}

    def fake_popen(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        alive["value"] = True

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(cli, "_server_alive", lambda port: alive["value"])
    return calls


class TestTokenHilfen:
    def test_neues_token_ist_zufaellig_und_lang_genug(self):
        a, b = auth_mod.new_token(), auth_mod.new_token()
        assert a != b
        assert len(a) >= 40

    def test_token_datei_ist_nur_fuer_den_eigentuemer_lesbar(self, token_dir):
        path = auth_mod.write_token_file(4750, ENV_TOKEN)
        assert path.parent == token_dir
        assert auth_mod.read_token_file(4750) == ENV_TOKEN
        if os.name == "posix":
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            assert stat.S_IMODE(token_dir.stat().st_mode) == 0o700

    def test_token_datei_wird_bei_bestehender_datei_wieder_auf_0600_gesetzt(self, token_dir):
        token_dir.mkdir()
        path = token_dir / "token-4750"
        path.write_text("alt")
        path.chmod(0o644)
        auth_mod.write_token_file(4750, ENV_TOKEN)
        assert auth_mod.read_token_file(4750) == ENV_TOKEN
        if os.name == "posix":
            assert stat.S_IMODE(path.stat().st_mode) == 0o600

    def test_fehlende_token_datei_ergibt_none(self):
        assert auth_mod.read_token_file(4799) is None

    @pytest.mark.parametrize(
        ("url", "erwartet"),
        [
            ("http://127.0.0.1:4750/", "http://127.0.0.1:4750/?token=abc"),
            ("http://127.0.0.1:4750/p/x?static=1", "http://127.0.0.1:4750/p/x?static=1&token=abc"),
        ],
    )
    def test_url_mit_token(self, url, erwartet):
        assert auth_mod.url_with_token(url, "abc") == erwartet

    def test_auth_header(self):
        assert auth_mod.auth_headers("abc") == {"X-Backlot-Token": "abc"}


class TestOpen:
    def test_startet_server_mit_neuem_token_in_der_umgebung_nicht_in_argv(self, spawned, opened, capsys):
        assert cli.cmd_open("film") == 0

        assert len(spawned) == 1
        token = spawned[0]["env"][auth_mod.TOKEN_ENV]
        assert len(token) >= 40
        assert token not in " ".join(spawned[0]["cmd"])
        assert opened == [f"http://127.0.0.1:4750/p/film?token={token}"]
        assert f"?token={token}" in capsys.readouterr().out

    def test_vorgegebenes_token_aus_der_umgebung_wird_genutzt(self, spawned, opened, monkeypatch):
        monkeypatch.setenv(auth_mod.TOKEN_ENV, ENV_TOKEN)
        assert cli.cmd_open(None) == 0
        assert spawned[0]["env"][auth_mod.TOKEN_ENV] == ENV_TOKEN
        assert opened == [f"http://127.0.0.1:4750/?token={ENV_TOKEN}"]

    def test_laufender_server_token_kommt_aus_der_token_datei(self, opened, monkeypatch):
        monkeypatch.setattr(cli, "_server_alive", lambda port: True)
        auth_mod.write_token_file(4750, ENV_TOKEN)
        assert cli.cmd_open("film") == 0
        assert opened == [f"http://127.0.0.1:4750/p/film?token={ENV_TOKEN}"]

    def test_laufender_server_ohne_bekanntes_token_oeffnet_url_ohne_token_und_warnt(
        self, opened, monkeypatch, capsys
    ):
        monkeypatch.setattr(cli, "_server_alive", lambda port: True)
        assert cli.cmd_open(None) == 0
        assert opened == ["http://127.0.0.1:4750/"]
        assert "token" in capsys.readouterr().out.lower()


class TestServe:
    @pytest.fixture(autouse=True)
    def kein_laufender_server(self, monkeypatch):
        monkeypatch.setattr(cli, "_server_alive", lambda port: False)

    def test_serve_schreibt_token_datei_und_uebergibt_token_an_die_app(self, monkeypatch, capsys):
        captured: dict = {}

        def fake_run(app, **kwargs):
            captured["app"] = app
            captured["kwargs"] = kwargs
            captured["file_token"] = auth_mod.read_token_file(4750)

        monkeypatch.setitem(sys.modules, "uvicorn", type(sys)("uvicorn"))
        sys.modules["uvicorn"].run = fake_run
        monkeypatch.setenv(auth_mod.TOKEN_ENV, ENV_TOKEN)

        assert cli.cmd_serve(4750) == 0

        assert captured["kwargs"]["host"] == "127.0.0.1"
        assert captured["kwargs"]["port"] == 4750
        assert captured["file_token"] == ENV_TOKEN
        assert captured["app"].state.backlot_token == ENV_TOKEN
        # Nach dem Beenden wird die Token-Datei aufgeräumt.
        assert auth_mod.read_token_file(4750) is None
        assert f"?token={ENV_TOKEN}" in capsys.readouterr().out

    def test_serve_ohne_vorgabe_erzeugt_token(self, monkeypatch):
        captured: dict = {}
        monkeypatch.setitem(sys.modules, "uvicorn", type(sys)("uvicorn"))
        sys.modules["uvicorn"].run = lambda app, **kw: captured.setdefault("app", app)
        assert cli.cmd_serve(4750) == 0
        assert len(captured["app"].state.backlot_token) >= 40

    def test_serve_lehnt_zu_kurzes_token_aus_der_umgebung_ab(self, monkeypatch, capsys):
        monkeypatch.setenv(auth_mod.TOKEN_ENV, "kurz")
        assert cli.cmd_serve(4750) == 2
        assert auth_mod.TOKEN_ENV in capsys.readouterr().err

    def test_serve_ueberschreibt_token_datei_eines_laufenden_servers_nicht(self, monkeypatch, capsys):
        auth_mod.write_token_file(4750, ENV_TOKEN)
        monkeypatch.setattr(cli, "_server_alive", lambda port: True)
        monkeypatch.setitem(sys.modules, "uvicorn", type(sys)("uvicorn"))
        sys.modules["uvicorn"].run = lambda app, **kw: pytest.fail("darf nicht starten")

        assert cli.cmd_serve(4750) == 1
        assert auth_mod.read_token_file(4750) == ENV_TOKEN
        assert "already" in capsys.readouterr().err

    @pytest.mark.skipif(os.name != "posix", reason="SIGTERM-Verhalten nur unter POSIX")
    def test_serve_raeumt_token_datei_auch_bei_sigterm_auf(self, monkeypatch):
        import signal

        def fake_run(app, **kwargs):
            # So beendet sich uvicorn: Nach dem Herunterfahren wird SIGTERM erneut ausgelöst.
            signal.raise_signal(signal.SIGTERM)

        monkeypatch.setitem(sys.modules, "uvicorn", type(sys)("uvicorn"))
        sys.modules["uvicorn"].run = fake_run
        monkeypatch.setenv(auth_mod.TOKEN_ENV, ENV_TOKEN)
        vorher = signal.getsignal(signal.SIGTERM)

        with pytest.raises(SystemExit):
            cli.cmd_serve(4750)

        assert auth_mod.read_token_file(4750) is None
        assert signal.getsignal(signal.SIGTERM) is vorher
