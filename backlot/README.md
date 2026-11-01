# Backlot — the living storyboard

A read-only local board that shows a production happening: pipeline stages
lighting up, the script as a screenplay page, the scene plan as a filmstrip
that fills in as assets generate, decisions, spend, and activity — all
derived from what the pipeline already writes to `projects/<id>/`.

```bash
python -m backlot open <project-id>   # start server if needed + open browser
python -m backlot open                # library view (all projects)
python -m backlot serve --port 4750   # run the server in the foreground (prints the URL with token)
```

## Access token

The server listens on 127.0.0.1 only, but other users of the same machine
could still reach it. Every request therefore needs a random token:

- `open` and `serve` create one per server start (`secrets.token_urlsafe`)
  unless `BACKLOT_TOKEN` is set (≥ 16 chars of `A-Z a-z 0-9 . _ ~ -`), and
  print/open the URL with `?token=…`. `open` passes the token to the spawned
  server via the environment, never on the command line.
- The browser trades `?token=` for a cookie `backlot_token_<port>`
  (HttpOnly, SameSite=Strict, Path=/, 30 days) and is redirected to the same
  URL without the token. Pages, SSE, `/media` (incl. range requests) and
  `/thumb` then work with the cookie.
- Scripts send `Authorization: Bearer <token>` or `X-Backlot-Token: <token>`.
  The running server's token is in `.backlot/auth/token-<port>` (mode 0600,
  removed on shutdown); `python -m backlot open` reads it when the server is
  already running.
- Everything else gets `401` with a short hint. Only `/api/health` answers
  without a token (no project data), so scripts can check that the server is
  up.

After a server restart the old cookie is invalid: run `python -m backlot open`
again for a fresh link. In code, `backlot.server.create_app(token=...)` always
requires a token (without one it generates a random one).

## How it stays live

No agent involvement. A `watchfiles` watcher on `projects/` publishes change
notifications over SSE; the browser refetches board state. State sources:

| Board element | Disk source |
|---|---|
| identity / rail order | `project.json` + `pipeline_defs/<type>.yaml` |
| stage states, gates, versions | `checkpoint_<stage>.json` + `history/` |
| script card / modal | `artifacts/script.json` |
| filmstrip cards | `scene_plan × script × asset_manifest` join |
| generating shimmer, activity | `events.jsonl` (written by `BaseTool` instrumentation) |
| cost meter | checkpoint `cost_snapshot` |
| renders | `renders/*.mp4` (+ root-level mp4 heuristic) |

Projects without checkpoints degrade gracefully to a "what the watcher
found" view — media, snapshots, renders.

**Replay**: a completed run can be scrubbed end-to-end (▶ REPLAY RUN on the
board) — reconstructed from checkpoint history and event timestamps.

Try it without a real production:

```bash
python scripts/backlot_simulate_run.py          # live demo run (~1 min)
python -m backlot open backlot-demo-run
```

Design doc: `internal/design/LIVING_STORYBOARD.md`.
