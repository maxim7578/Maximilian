"""Server/API tests for Backlot.

These cover the deterministic eval surface in internal/evals/BACKLOT_EVAL_PLAN.md:
API shape, path safety, media/thumb serving, range requests, and loose
performance budgets.
"""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backlot import auth as auth_mod
from backlot import server as server_mod
from backlot import state as state_mod

TEST_TOKEN = "test-token-" + "x" * 32
BASE_URL = "http://127.0.0.1:4750"
COOKIE_NAME = auth_mod.cookie_name(4750)


@pytest.fixture
def projects_root(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr(state_mod, "PROJECTS_DIR", root)
    monkeypatch.setattr(server_mod, "PROJECTS_DIR", root)
    monkeypatch.setattr(server_mod, "_summary_cache", {})
    monkeypatch.setattr(server_mod, "_PROJECTS_ROOT_STR", __import__("os").path.normcase(str(root.resolve())))
    monkeypatch.setattr(server_mod, "THUMB_CACHE_DIR", tmp_path / "thumbs")
    return root


@pytest.fixture
def app(projects_root, monkeypatch):
    async def no_watch():
        return None

    monkeypatch.setattr(server_mod, "_watch_projects", no_watch)
    return server_mod.create_app(token=TEST_TOKEN)


@pytest.fixture
def client(app):
    """Angemeldeter Client: hat das Token-Cookie wie ein Browser nach dem Öffnen der URL."""
    # Wie im Browser: Der Server ist nur unter 127.0.0.1/localhost erreichbar.
    with TestClient(app, base_url=BASE_URL) as c:
        c.cookies.set(COOKIE_NAME, TEST_TOKEN)
        yield c


@pytest.fixture
def anon_client(app):
    """Client ohne Token, z. B. ein anderer lokaler Benutzer."""
    with TestClient(app, base_url=BASE_URL, follow_redirects=False) as c:
        yield c


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_project(root: Path, project_id: str = "film") -> Path:
    project = root / project_id
    (project / "artifacts").mkdir(parents=True)
    (project / "assets" / "images").mkdir(parents=True)
    (project / "assets" / "video").mkdir(parents=True)
    (project / "renders").mkdir(parents=True)
    _write_json(
        project / "project.json",
        {
            "project_id": project_id,
            "title": "Film",
            "pipeline_type": "cinematic",
            "created_at": "2026-07-02T00:00:00Z",
        },
    )
    _write_json(
        project / "checkpoint_script.json",
        {
            "version": "1.0",
            "project_id": project_id,
            "pipeline_type": "cinematic",
            "stage": "script",
            "status": "awaiting_human",
            "timestamp": "2026-07-02T00:01:00Z",
            "artifacts": {},
        },
    )
    return project


def _write_png(path: Path, color: tuple[int, int, int] = (200, 40, 80)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (24, 16), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    path.write_bytes(buf.getvalue())


class TestBacklotServerApi:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True, "app": "backlot"}

    def test_projects_shape_and_state(self, client, projects_root):
        _make_project(projects_root, "film")

        projects = client.get("/api/projects")
        assert projects.status_code == 200
        body = projects.json()
        assert len(body) == 1
        assert body[0]["project_id"] == "film"
        assert body[0]["awaiting_human"] is True
        assert "stage_states" in body[0]

        state = client.get("/api/project/film/state")
        assert state.status_code == 200
        state_body = state.json()
        assert state_body["project_id"] == "film"
        assert state_body["title"] == "Film"
        assert state_body["stages"]

    @pytest.mark.parametrize(
        ("url", "status"),
        [
            ("/api/project/../state", 404),
            ("/api/project/C:/state", 400),
            ("/api/project/nope/state", 404),
        ],
    )
    def test_project_id_rejects_bad_or_unknown_ids(self, client, url, status):
        response = client.get(url)
        assert response.status_code == status

    def test_media_rejects_path_traversal(self, client, projects_root):
        _make_project(projects_root, "film")
        response = client.get("/media/film/%2E%2E/project.json")
        assert response.status_code == 403

    def test_media_serves_range_requests(self, client, projects_root):
        project = _make_project(projects_root, "film")
        media = project / "renders" / "final.mp4"
        media.write_bytes(b"0123456789")

        response = client.get("/media/film/renders/final.mp4", headers={"Range": "bytes=2-5"})

        assert response.status_code == 206
        assert response.content == b"2345"
        assert response.headers["content-range"].startswith("bytes 2-5/10")

    def test_thumb_downscales_image_and_passes_through_non_media(self, client, projects_root):
        project = _make_project(projects_root, "film")
        _write_png(project / "assets" / "images" / "sc1.png")
        text = project / "artifacts" / "note.txt"
        text.write_text("hello", encoding="utf-8")

        image = client.get("/thumb/film/assets/images/sc1.png?w=320")
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/jpeg"
        assert image.content.startswith(b"\xff\xd8")

        passthrough = client.get("/thumb/film/artifacts/note.txt")
        assert passthrough.status_code == 200
        assert passthrough.content == b"hello"


class TestBacklotPerformanceBudgets:
    def test_projects_and_state_stay_within_loose_budgets(self, client, projects_root):
        for i in range(25):
            project = _make_project(projects_root, f"film-{i:02d}")
            _write_json(
                project / "artifacts" / "scene_plan.json",
                {"version": "1.0", "scenes": [{"id": "sc1", "start_seconds": 0, "end_seconds": 1}]},
            )

        t0 = time.perf_counter()
        cold = client.get("/api/projects")
        cold_s = time.perf_counter() - t0
        assert cold.status_code == 200
        assert cold_s < 2.0

        t1 = time.perf_counter()
        warm = client.get("/api/projects")
        warm_s = time.perf_counter() - t1
        assert warm.status_code == 200
        assert warm_s < 0.150

        t2 = time.perf_counter()
        state = client.get("/api/project/film-00/state")
        state_s = time.perf_counter() - t2
        assert state.status_code == 200
        assert state_s < 0.400

    def test_image_thumb_generation_stays_within_budget(self, client, projects_root):
        project = _make_project(projects_root, "film")
        _write_png(project / "assets" / "images" / "sc1.png")

        t0 = time.perf_counter()
        response = client.get("/thumb/film/assets/images/sc1.png?w=640")
        elapsed = time.perf_counter() - t0

        assert response.status_code == 200
        assert elapsed < 1.5


class TestFindingsFixes:
    """Regression tests for dogfood findings F-03 (thumb video fallback)."""

    def test_thumb_never_serves_raw_video_bytes(self, client, projects_root):
        p = _make_project(projects_root, "vid")
        fake_video = p / "renders" / "final.mp4"
        fake_video.parent.mkdir(parents=True, exist_ok=True)
        # Not a real video: ffmpeg poster extraction will fail.
        fake_video.write_bytes(b"\x00" * 4096)
        res = client.get("/thumb/vid/renders/final.mp4")
        assert res.status_code == 404  # never the raw video bytes (F-03)


class TestSicherheit:
    """Befunde M6/M7 aus docs/sicherheitspruefung-2026-11-01.md."""

    def test_fremder_host_wird_abgelehnt(self, client, projects_root):
        # DNS-Rebinding: Eine fremde Webseite zeigt mit ihrer Domain auf 127.0.0.1.
        _make_project(projects_root, "film")
        res = client.get("/api/projects", headers={"Host": "evil.example:4750"})
        assert res.status_code == 400

    @pytest.mark.parametrize("host", ["127.0.0.1:4750", "localhost:4750"])
    def test_lokaler_host_ist_erlaubt(self, client, projects_root, host):
        res = client.get("/api/health", headers={"Host": host})
        assert res.status_code == 200

    @pytest.mark.parametrize("name", ["seite.html", "bild.svg", "final.mp4"])
    def test_medien_koennen_kein_skript_ausfuehren(self, client, projects_root, name):
        project = _make_project(projects_root, "film")
        (project / "renders" / name).write_text("<script>alert(1)</script>", encoding="utf-8")
        res = client.get(f"/media/film/renders/{name}")
        assert res.status_code == 200
        assert "sandbox" in res.headers["content-security-policy"]
        assert res.headers["x-content-type-options"] == "nosniff"

    def test_vorschaubild_kann_kein_skript_ausfuehren(self, client, projects_root):
        project = _make_project(projects_root, "film")
        (project / "assets" / "images" / "logo.svg").write_text("<svg><script>alert(1)</script></svg>", encoding="utf-8")
        res = client.get("/thumb/film/assets/images/logo.svg")
        assert res.status_code == 200
        assert "sandbox" in res.headers["content-security-policy"]


class TestZugriffsschutz:
    """Befund N12: Ohne Token darf niemand Projekte, Medien oder Seiten lesen."""

    GESCHUETZTE_PFADE = [
        "/",
        "/p/film",
        "/p/film?static=1",
        "/api/projects",
        "/api/project/film/state",
        "/api/project/film/events",
        "/api/library/events",
        "/media/film/renders/final.mp4",
        "/thumb/film/assets/images/sc1.png",
        "/ui/board.js",
    ]

    @pytest.fixture
    def film(self, projects_root):
        project = _make_project(projects_root, "film")
        (project / "renders" / "final.mp4").write_bytes(b"0123456789")
        _write_png(project / "assets" / "images" / "sc1.png")
        return project

    @pytest.mark.parametrize("pfad", GESCHUETZTE_PFADE)
    def test_ohne_token_wird_alles_ausser_health_abgelehnt(self, anon_client, film, pfad):
        res = anon_client.get(pfad)
        assert res.status_code == 401
        assert res.headers["content-type"].startswith("text/plain")
        assert "token" in res.text.lower()
        assert "Film" not in res.text
        assert "set-cookie" not in res.headers

    def test_health_antwortet_ohne_token_und_ohne_projektdaten(self, anon_client, film):
        res = anon_client.get("/api/health")
        assert res.status_code == 200
        assert res.json() == {"ok": True, "app": "backlot"}
        assert "set-cookie" not in res.headers

    def test_gueltiges_token_in_url_setzt_cookie_und_leitet_ohne_token_um(self, anon_client, film):
        res = anon_client.get(f"/p/film?static=1&token={TEST_TOKEN}")
        assert res.status_code == 303
        assert res.headers["location"] == "/p/film?static=1"
        cookie = res.headers["set-cookie"]
        assert cookie.startswith(f"{COOKIE_NAME}={TEST_TOKEN};")
        assert "HttpOnly" in cookie
        assert "SameSite=Strict" in cookie
        assert "Path=/" in cookie
        assert "Domain" not in cookie

    def test_umleitung_ohne_weitere_parameter_und_mit_kodiertem_pfad(self, anon_client, film):
        res = anon_client.get(f"/?token={TEST_TOKEN}")
        assert res.status_code == 303
        assert res.headers["location"] == "/"
        res = anon_client.get(f"/p/..%2FAGENT_GUIDE.md?token={TEST_TOKEN}&static=1")
        assert res.status_code == 303
        assert res.headers["location"] == "/p/..%2FAGENT_GUIDE.md?static=1"

    @pytest.mark.parametrize("falsch", ["falsch", TEST_TOKEN + "x", TEST_TOKEN[:-1], ""])
    def test_falsches_token_in_url_wird_abgelehnt(self, anon_client, film, falsch):
        res = anon_client.get(f"/api/projects?token={falsch}")
        assert res.status_code == 401
        assert "set-cookie" not in res.headers

    def test_falsches_token_in_url_wird_auch_mit_gueltigem_cookie_abgelehnt(self, client, film):
        res = client.get("/api/projects?token=falsch", follow_redirects=False)
        assert res.status_code == 401

    def test_falsches_cookie_wird_abgelehnt(self, anon_client, film):
        anon_client.cookies.set(COOKIE_NAME, "falsch")
        assert anon_client.get("/api/projects").status_code == 401

    def test_cookie_eines_anderen_ports_reicht_nicht(self, anon_client, film):
        anon_client.cookies.set(auth_mod.cookie_name(4751), TEST_TOKEN)
        assert anon_client.get("/api/projects").status_code == 401

    def test_nach_umleitung_reicht_das_cookie_fuer_api_seiten_und_medien(self, anon_client, film):
        first = anon_client.get(f"/?token={TEST_TOKEN}")
        assert first.status_code == 303

        assert anon_client.get("/").status_code == 200
        assert anon_client.get("/p/film").status_code == 200
        assert anon_client.get("/ui/board.js").status_code == 200
        projects = anon_client.get("/api/projects")
        assert projects.status_code == 200
        assert projects.json()[0]["project_id"] == "film"
        assert anon_client.get("/api/project/film/state").status_code == 200
        thumb = anon_client.get("/thumb/film/assets/images/sc1.png?w=320")
        assert thumb.status_code == 200
        assert thumb.headers["content-type"] == "image/jpeg"

        ranged = anon_client.get("/media/film/renders/final.mp4", headers={"Range": "bytes=2-5"})
        assert ranged.status_code == 206
        assert ranged.content == b"2345"

    def test_sse_endpunkt_ist_mit_cookie_erreichbar(self, client, film):
        # Unbekanntes Projekt: Die Anfrage kommt am Token vorbei bis zum Endpunkt (404 statt 401).
        assert client.get("/api/project/nope/events").status_code == 404

    @pytest.mark.parametrize(
        "header",
        [
            {"Authorization": f"Bearer {TEST_TOKEN}"},
            {"X-Backlot-Token": TEST_TOKEN},
        ],
    )
    def test_skripte_koennen_sich_per_header_anmelden(self, anon_client, film, header):
        res = anon_client.get("/api/projects", headers=header)
        assert res.status_code == 200
        assert "set-cookie" not in res.headers

    @pytest.mark.parametrize(
        "header",
        [
            {"Authorization": "Bearer falsch"},
            {"Authorization": f"Basic {TEST_TOKEN}"},
            {"X-Backlot-Token": "falsch"},
        ],
    )
    def test_falscher_header_wird_abgelehnt(self, anon_client, film, header):
        assert anon_client.get("/api/projects", headers=header).status_code == 401

    def test_fremder_host_wird_auch_mit_token_abgelehnt(self, anon_client, film):
        res = anon_client.get(f"/?token={TEST_TOKEN}", headers={"Host": "evil.example:4750"})
        assert res.status_code == 400
        assert "set-cookie" not in res.headers

    @pytest.mark.parametrize("token", ["", "kurz"])
    def test_create_app_lehnt_leeres_oder_zu_kurzes_token_ab(self, projects_root, token):
        with pytest.raises(ValueError):
            server_mod.create_app(token=token)

    def test_create_app_ohne_token_erzeugt_ein_zufaelliges(self, projects_root, monkeypatch):
        async def no_watch():
            return None

        monkeypatch.setattr(server_mod, "_watch_projects", no_watch)
        with TestClient(server_mod.create_app(), base_url=BASE_URL) as c:
            assert c.get("/api/projects").status_code == 401
            assert c.get("/api/health").status_code == 200


class TestEchterServerMitCookie:
    """Ende-zu-Ende mit uvicorn: SSE-Strom und Range-Anfrage laufen mit dem Cookie."""

    @pytest.fixture
    def live_server(self, app, projects_root, monkeypatch):
        import socket
        import threading

        import uvicorn

        monkeypatch.setattr(server_mod, "SSE_HEARTBEAT_SECONDS", 0.2)
        project = _make_project(projects_root, "film")
        (project / "renders" / "final.mp4").write_bytes(b"0123456789")

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        config = uvicorn.Config(app, log_level="warning", timeout_graceful_shutdown=1)
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        deadline = time.time() + 10
        while not server.started and time.time() < deadline:
            time.sleep(0.05)
        assert server.started
        try:
            yield port
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()

    def test_sse_und_range_mit_cookie_aus_der_token_url(self, live_server):
        import httpx

        port = live_server
        base = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=base, follow_redirects=True, timeout=5) as http:
            assert http.get("/api/projects").status_code == 401
            page = http.get(f"/p/film?token={TEST_TOKEN}")
            assert page.status_code == 200
            assert str(page.url) == f"{base}/p/film"
            assert http.cookies.get(auth_mod.cookie_name(port)) == TEST_TOKEN

            ranged = http.get("/media/film/renders/final.mp4", headers={"Range": "bytes=0-3"})
            assert ranged.status_code == 206
            assert ranged.content == b"0123"

            with http.stream("GET", "/api/project/film/events") as stream:
                assert stream.status_code == 200
                assert stream.headers["content-type"].startswith("text/event-stream")
                first = next(stream.iter_lines())
                assert json.loads(first.removeprefix("data: "))["type"] == "hello"
