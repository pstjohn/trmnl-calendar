# Repository Guidelines

## Project Structure & Module Organization

This package renders and serves a TRMNL weekly calendar image.

- `src/trmnl_weekly_calendar/render.py`: Pillow renderer, mock data, layout constants, and image output.
- `src/trmnl_weekly_calendar/calendar_data.py`: live calendar loading and normalization from optional `gog` output.
- `src/trmnl_weekly_calendar/server.py`: `/trmnl.json`, `/image.png`, and `/healthz` routes.
- `assets/fonts/`: vendored renderer fonts.
- `outputs/`: generated reference PNGs.
- `docs/agent-plans/`: implementation notes and progress plans.

## Build, Test, and Development Commands

- `uv sync` installs the locked environment from `pyproject.toml` and `uv.lock`.
- `uv run render-trmnl-calendar` renders the mock weekly calendar into `outputs/`.
- `uv run serve-trmnl-calendar` starts the local HTTP server, defaulting to `0.0.0.0:8787`.
- `python3 -m compileall src` performs lightweight syntax/import validation.

## Systemd Service Operations

The persistent server is `trmnl-calendar.service` at `/etc/systemd/system/trmnl-calendar.service`. It runs as `ubuntu` from `/home/ubuntu/trmnl-calendar`, loads `/home/ubuntu/.hermes/.env`, and starts `/home/ubuntu/.local/bin/uv run serve-trmnl-calendar`. It listens on `0.0.0.0:8787`, uses `America/Denver`, refreshes every `900` seconds, outputs `4bit`, and loads live events with `/usr/local/bin/gog`.

- `systemctl status trmnl-calendar.service --no-pager` checks runtime state.
- `journalctl -u trmnl-calendar.service -n 100 --no-pager` reviews recent logs.
- `uv sync && sudo systemctl restart trmnl-calendar.service` reinitializes after code or dependency changes.
- `sudo systemctl daemon-reload && sudo systemctl restart trmnl-calendar.service` reinitializes after editing the unit or environment file.
- `sudo systemctl enable --now trmnl-calendar.service` enables boot startup.
- `curl http://127.0.0.1:8787/healthz` verifies the HTTP surface; also check `/trmnl.json` and `/image.png`.

## Coding Style & Naming Conventions

Use Python 3.11+ syntax, 4-space indentation, and type hints for public helpers or non-obvious data. Group imports as standard library, third-party, then local. Prefer `dataclass` models and `pathlib.Path`. Use uppercase constants, `snake_case` functions/variables, and `PascalCase` classes.

No formatter or linter configuration is checked in. Keep changes Black-compatible and avoid broad refactors unless needed.

## Testing Guidelines

There is no dedicated test suite yet. For renderer changes, run `uv run render-trmnl-calendar` and inspect `outputs/`. For server changes, check `/healthz`, `/trmnl.json`, and `/image.png`. For parser changes, add focused `tests/test_*.py` files.

## Security & Configuration Tips

Do not commit secrets, account names, private calendar output, or local `.venv/` contents. Treat `GOG_ACCOUNT` and generated live-calendar images as potentially sensitive.
