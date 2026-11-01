"""Tests for the Backlot dogfood screenshot watcher helpers."""

import io
import json

from backlot import auth as auth_mod
from scripts import backlot_watch_captures as watch_mod
from scripts.backlot_watch_captures import capture_slug, state_fingerprint


def test_capture_slug_keeps_names_filesystem_safe():
    assert capture_slug("why-cities-glow", "scene_plan", "awaiting_human") == (
        "why-cities-glow-scene_plan-awaiting_human"
    )
    assert capture_slug("../bad id", "C:\\stage", "in progress!") == "bad-id-C-stage-in-progress"


def test_state_fingerprint_changes_on_board_relevant_state_only():
    state = {
        "stages": [
            {"name": "script", "status": "completed", "partial_progress": None},
            {"name": "assets", "status": "in_progress", "partial_progress": {"done": ["sc1"]}},
        ],
        "storyboard": {
            "scenes": [
                {
                    "id": "sc1",
                    "generating": False,
                    "visual": {"path": "assets/images/sc1.png", "exists": True},
                    "takes": [{"path": "assets/images/sc1.png"}],
                },
                {"id": "sc2", "generating": True, "generating_tool": "flux_image", "visual": None},
            ]
        },
        "cost": {"total_spent_usd": 0.1},
        "media": {"renders": []},
        "events": [{"event": "start", "tool": "flux_image"}],
        "last_activity": 123,
    }
    same = dict(state)
    same["last_activity"] = 999

    changed = dict(state)
    changed["storyboard"] = {
        "scenes": [
            state["storyboard"]["scenes"][0],
            {"id": "sc2", "generating": False, "visual": {"path": "assets/images/sc2.png", "exists": True}},
        ]
    }

    assert state_fingerprint(state) == state_fingerprint(same)
    assert state_fingerprint(state) != state_fingerprint(changed)


def test_fetch_json_schickt_das_token_als_header(monkeypatch):
    gesehen = {}

    class Antwort(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout):
        gesehen["url"] = request.full_url
        gesehen["header"] = request.get_header("X-backlot-token")
        return Antwort(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(watch_mod.urllib.request, "urlopen", fake_urlopen)
    assert watch_mod.fetch_json("http://127.0.0.1:4750/", "/api/projects", "geheim") == {"ok": True}
    assert gesehen == {"url": "http://127.0.0.1:4750/api/projects", "header": "geheim"}


def test_server_token_reihenfolge_argument_umgebung_datei(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_mod, "TOKEN_DIR", tmp_path)
    monkeypatch.delenv(auth_mod.TOKEN_ENV, raising=False)
    base = "http://127.0.0.1:4777"
    assert watch_mod.server_token(base) is None

    auth_mod.write_token_file(4777, "aus-der-datei")
    assert watch_mod.server_token(base) == "aus-der-datei"

    monkeypatch.setenv(auth_mod.TOKEN_ENV, "aus-der-umgebung")
    assert watch_mod.server_token(base) == "aus-der-umgebung"
    assert watch_mod.server_token(base, "vom-argument") == "vom-argument"
