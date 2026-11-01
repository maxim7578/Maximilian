"""Backlot CLI.

    python -m backlot open [project-id]   # start server if needed, open browser
    python -m backlot serve [--port N]    # run the server in the foreground

``open`` is idempotent and non-fatal by design: agents call it at pipeline
initialization and must continue the production even if it fails.

Access needs a random token (``BACKLOT_TOKEN`` or generated at start). ``open``
and ``serve`` print/open the URL with ``?token=...``; the browser then keeps it
in a cookie. The running server's token is in ``.backlot/auth/token-<port>``
(mode 0600) so later ``open`` calls and scripts can find it.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser

from backlot import DEFAULT_PORT
from backlot import auth


def _port() -> int:
    try:
        return int(os.environ.get("BACKLOT_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT


def _server_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _spawn_server(port: int, token: str) -> None:
    """Start the server as a detached background process."""
    cmd = [sys.executable, "-m", "backlot", "serve", "--port", str(port)]
    # Token über die Umgebung, nie über argv: Die Befehlszeile sieht jeder Benutzer (ps).
    kwargs: dict = {
        "env": {**os.environ, auth.TOKEN_ENV: token},
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def cmd_open(project_id: str | None) -> int:
    port = _port()
    if _server_alive(port):
        token = auth.resolve_token(port, prefer_file=True)
    else:
        token = auth.resolve_token(port, prefer_file=False) or auth.new_token()
        try:
            _spawn_server(port, token)
        except Exception as exc:
            print(f"backlot: could not start server ({exc}) — continuing without the board")
            return 1
        deadline = time.time() + 15
        while time.time() < deadline:
            if _server_alive(port):
                break
            time.sleep(0.4)
        else:
            print("backlot: server did not come up in time — continuing without the board")
            return 1
    url = f"http://127.0.0.1:{port}/"
    if project_id:
        url = f"http://127.0.0.1:{port}/p/{project_id}"
    if token:
        url = auth.url_with_token(url, token)
    else:
        print(f"backlot: token of the running server unknown (set {auth.TOKEN_ENV} "
              f"or restart it) — the board will answer 401")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print(f"backlot: {url}")
    return 0


def cmd_serve(port: int) -> int:
    import uvicorn

    from backlot.server import create_app

    if _server_alive(port):
        # Sonst würde die Token-Datei des laufenden Servers überschrieben.
        print(f"backlot: a server is already running on port {port}", file=sys.stderr)
        return 1
    token = auth.resolve_token(port, prefer_file=False) or auth.new_token()
    try:
        app = create_app(token=token)
    except ValueError as exc:
        print(f"backlot: invalid {auth.TOKEN_ENV}: {exc}", file=sys.stderr)
        return 2
    auth.write_token_file(port, token)
    print(f"backlot: serving {auth.url_with_token(f'http://127.0.0.1:{port}/', token)}", flush=True)
    # uvicorn löst SIGTERM nach dem Herunterfahren erneut aus; ohne eigenen Handler
    # endet der Prozess sofort und die Token-Datei bliebe liegen.
    previous = signal.signal(signal.SIGTERM, _exit_on_sigterm)
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    finally:
        signal.signal(signal.SIGTERM, previous)
        auth.remove_token_file(port, token)
    return 0


def _exit_on_sigterm(signum, frame) -> None:
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="backlot", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_open = sub.add_parser("open", help="open the board in the browser (starts server if needed)")
    p_open.add_argument("project_id", nargs="?", default=None)

    p_serve = sub.add_parser("serve", help="run the Backlot server in the foreground")
    p_serve.add_argument("--port", type=int, default=_port())

    args = parser.parse_args(argv)
    if args.command == "open":
        return cmd_open(args.project_id)
    if args.command == "serve":
        return cmd_serve(args.port)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
