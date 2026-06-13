# Repository Guidelines

## Project Structure & Module Organization

This package renders and serves a TRMNL weekly calendar image.

- `src/trmnl_weekly_calendar/render.py`: Pillow renderer, mock data, layout constants, and image output.
- `src/trmnl_weekly_calendar/calendar_data.py`: live calendar loading and normalization from optional `gog` output.
- `src/trmnl_weekly_calendar/month_render.py`: Pillow renderer for the month plugin.
- `src/trmnl_weekly_calendar/server.py`: `/weekly/*`, `/month/*`, legacy weekly routes, and `/healthz`.
- `assets/fonts/`: vendored renderer fonts.
- `outputs/`: generated reference PNGs.
- `docs/agent-plans/`: implementation notes and progress plans.

## Build, Test, and Development Commands

- `uv sync` installs the locked environment from `pyproject.toml` and `uv.lock`.
- `uv run render-trmnl-calendar` renders the mock weekly calendar into `outputs/`.
- `uv run serve-trmnl-calendar` starts the local HTTP server, defaulting to `0.0.0.0:8787`.
- `python3 -m compileall src` performs lightweight syntax/import validation.

## Systemd Service Operations

The persistent server is `trmnl-calendar.service` at `/etc/systemd/system/trmnl-calendar.service`. It runs as `ubuntu` from `/home/ubuntu/trmnl-calendar`, loads `/home/ubuntu/.hermes/.env`, and starts `/home/ubuntu/.local/bin/uv run serve-trmnl-calendar`. It listens on `0.0.0.0:8787`, uses `America/Denver`, refreshes rendered images every `900` seconds, caches live calendar data for `7200` seconds by default, outputs `4bit`, and loads live events with `/usr/local/bin/gog`.

- `systemctl status trmnl-calendar.service --no-pager` checks runtime state.
- `journalctl -u trmnl-calendar.service -n 100 --no-pager` reviews recent logs.
- `uv sync && sudo systemctl restart trmnl-calendar.service` reinitializes after code or dependency changes.
- `sudo systemctl daemon-reload && sudo systemctl restart trmnl-calendar.service` reinitializes after editing the unit or environment file.
- `sudo systemctl enable --now trmnl-calendar.service` enables boot startup.
- `curl http://127.0.0.1:8787/healthz` verifies the HTTP surface; also check `/weekly/trmnl.json`, `/weekly/image.png`, `/month/trmnl.json`, and `/month/image.png`.

## TRMNL Redirect Contract

The device should be configured against the public Redirect JSON endpoint:

```text
https://trmnl-weekly-3aub7nlf6.brevlab.com/trmnl.json
```

Additional plugins are served as separate URL paths from the same server process:

```text
https://trmnl-weekly-3aub7nlf6.brevlab.com/weekly/trmnl.json
https://trmnl-weekly-3aub7nlf6.brevlab.com/month/trmnl.json
```

The root `/trmnl.json` and `/image.png` paths are legacy aliases for the weekly plugin.

The `/trmnl.json` response must stay small and fast. TRMNL documents a strict 2-second timeout for the Redirect plugin JSON request. The JSON shape is:

```json
{"filename":"weekly-calendar-<fingerprint>","url":"https://.../image.png?v=<fingerprint>","refresh_rate":900}
```

- `filename` is TRMNL's diff key. Keep it stable when image bytes are unchanged to avoid unnecessary screen refresh/flicker.
- `url` points at the generated PNG. Include the fingerprint query parameter so changed images get a fresh URL.
- `refresh_rate` is seconds between device wakeups. The fastest documented cadence is once per minute.
- `/image.png` must return `Content-Type: image/png` and an integer `Content-Length`.
- This project targets TRMNL X full-screen output: `1872x1404`, 4:3, 16-level grayscale PNG. The older Redirect article calls out OG-style `800x480` 1-bit PNG/BMP3; do not downscale unless explicitly targeting OG hardware.
- Use normal `/weekly/trmnl.json` or `/month/trmnl.json` for the device. Use `?refresh=1&ts=<unique>` only for local/manual iteration, because it bypasses both the rendered-image cache and the shared calendar-data cache.
- BrevLab may rewrite public cache headers. When manually forcing a public image refresh, change the query string, for example `/image.png?refresh=1&ts=20260613T121930Z`.

## Coding Style & Naming Conventions

Use Python 3.11+ syntax, 4-space indentation, and type hints for public helpers or non-obvious data. Group imports as standard library, third-party, then local. Prefer `dataclass` models and `pathlib.Path`. Use uppercase constants, `snake_case` functions/variables, and `PascalCase` classes.

No formatter or linter configuration is checked in. Keep changes Black-compatible and avoid broad refactors unless needed.

## Testing Guidelines

There is no dedicated test suite yet. For renderer changes, run `uv run render-trmnl-calendar` and inspect `outputs/`. For server changes, check `/healthz`, `/trmnl.json`, and `/image.png`. For parser changes, add focused `tests/test_*.py` files.

## Security & Configuration Tips

Do not commit secrets, account names, private calendar output, or local `.venv/` contents. Treat `GOG_ACCOUNT` and generated live-calendar images as potentially sensitive.
