# Local Systemd Service Plan

## Goal

Run the TRMNL weekly calendar server locally with live Google Calendar data through the existing `gog` credentials, and install it as a systemd service that starts on boot and restarts on failure.

## Constraints

- Keep the app running as the existing `ubuntu` user so it can access the same Hermes-owned environment and credential paths.
- Do not expose or copy Google credentials into the repository.
- Use the repo's existing Python/`uv` workflow instead of adding a new process manager.
- Keep service config outside the repo under `/etc/systemd/system`.

## Discovered Context

- Repo path is `/home/ubuntu/trmnl-calendar`.
- The server entry point is `serve-trmnl-calendar`, backed by `src/trmnl_weekly_calendar/server.py`.
- Live events are enabled by setting `TRMNL_GOG_COMMAND`; without it the server renders mock data.
- `gog` is installed at `/usr/local/bin/gog`, but manual shells must source `/home/ubuntu/.hermes/.env` for `GOG_ACCOUNT` and `GOG_KEYRING_PASSWORD`.
- With that env loaded, `gog calendar events primary --account "$GOG_ACCOUNT" --from ... --to ... --json --no-input` returns event JSON successfully.
- `uv` is installed at `/home/ubuntu/.local/bin/uv`.
- System services already run Hermes components as `ubuntu`, loading `/home/ubuntu/.hermes/.env` through an `EnvironmentFile`.
- Port `8787` is currently free.

## Alternatives Considered

- Run the server manually in a shell.
  - Lowest setup cost, but it does not satisfy restart or boot persistence.
- Install a user-level systemd service.
  - Avoids root-owned unit files, but boot behavior depends on lingering/user manager state.
- Install a system-level service that runs as `ubuntu`.
  - Matches existing Hermes services, starts reliably on boot, and can load the same env file without moving secrets. This is the selected approach.

## Final Design

Create `/etc/systemd/system/trmnl-calendar.service` with:

- `User=ubuntu` and `Group=ubuntu`
- `WorkingDirectory=/home/ubuntu/trmnl-calendar`
- `EnvironmentFile=/home/ubuntu/.hermes/.env`
- `TRMNL_HOST=0.0.0.0`, `TRMNL_PORT=8787`, `TRMNL_TIMEZONE=America/Denver`, and `TRMNL_REFRESH_SECONDS=900`
- `TRMNL_GOG_COMMAND=/usr/local/bin/gog calendar events primary --account {account} --from {start} --to {end} --all-pages --json --no-input`, with `{account}` supplied from `GOG_ACCOUNT`
- `ExecStart=/home/ubuntu/.local/bin/uv run serve-trmnl-calendar`
- `Restart=always` and `RestartSec=5`

Enable and start the service, then verify health and image endpoints locally.

## Chunk List

### Chunk 1: Runtime Verification

- Objective: Confirm dependencies, Google Calendar access, and the server command work before installing the service.
- Files or areas likely to change: none.
- Dependencies on other chunks: none.
- Non-goals: changing renderer layout or calendar parsing behavior.
- Commands to run: `uv sync`, manual `gog calendar events`, manual `uv run serve-trmnl-calendar` if needed.
- Expected checks: dependency install succeeds and live calendar JSON is available.
- Blocker-report format: command, exit code, and the smallest relevant stderr/stdout excerpt.

### Chunk 2: Command Template Support

- Objective: Let the existing calendar loader substitute `GOG_ACCOUNT` via an `{account}` template value.
- Files or areas likely to change: `src/trmnl_weekly_calendar/calendar_data.py`, README if documentation needs a small update.
- Dependencies on other chunks: Chunk 1.
- Non-goals: adding OAuth flows or changing the event parser.
- Commands to run: `uv run python -m compileall src`.
- Expected checks: template formatting succeeds with `{account}` and existing `{start}`/`{end}` still work.
- Blocker-report format: file, failing command, and traceback excerpt.

### Chunk 3: Systemd Unit Installation

- Objective: Install a system service that runs the existing server with live Google Calendar env.
- Files or areas likely to change: `/etc/systemd/system/trmnl-calendar.service`.
- Dependencies on other chunks: Chunk 1 and Chunk 2.
- Non-goals: committing secrets or adding repo-local `.env` files.
- Commands to run: `sudo tee`, `sudo systemctl daemon-reload`, `sudo systemctl enable --now trmnl-calendar.service`.
- Expected checks: systemd reports service enabled and active.
- Blocker-report format: unit file path, failed systemctl command, and journal excerpt.

### Chunk 4: Endpoint Verification

- Objective: Verify the local HTTP surface for TRMNL.
- Files or areas likely to change: none.
- Dependencies on other chunks: Chunk 3.
- Non-goals: public URL or reverse proxy setup.
- Commands to run: `curl http://127.0.0.1:8787/healthz`, `curl http://127.0.0.1:8787/trmnl.json`, `curl -I http://127.0.0.1:8787/image.png`.
- Expected checks: health returns `ok`, redirect JSON contains image URL and refresh rate, image returns `Content-Type: image/png`.
- Blocker-report format: endpoint, status code, and service journal excerpt.

## Subagent Packets

- Not needed for this small operational setup. A single agent can inspect, install, and verify within one session.

## Acceptance Criteria

- `trmnl-calendar.service` is enabled and active.
- The service restarts automatically on failure and starts on machine boot.
- `/healthz` returns `ok`.
- `/trmnl.json` returns TRMNL Redirect-compatible JSON with refresh rate `900`.
- `/image.png` returns a PNG generated from live calendar data.
- No credentials or secret values are committed to the repository.

## Test Plan

- Run `uv sync`.
- Run a non-interactive `gog calendar events` command with Hermes env loaded.
- Start the service through systemd.
- Check `systemctl status trmnl-calendar.service`.
- Check `/healthz`, `/trmnl.json`, and `/image.png` with `curl`.
- Review recent journal entries for errors.

## Linear Links

- Not configured.

## Progress Log

- 2026-06-13: Inspected repo, verified `gog` access through `/home/ubuntu/.hermes/.env`, confirmed `uv` and systemd availability, and selected a system-level service running as `ubuntu`.
- 2026-06-13: Chunk 1 DONE. Ran `uv sync`, created the local virtualenv, and confirmed a non-interactive `gog calendar events` call returns JSON with Hermes env loaded.
- 2026-06-13: Chunk 2 DONE. Added `{account}` command-template support, documented the local Hermes command, ran `uv run python -m compileall src`, and verified `load_events()` returns live `gog` data with the new template.
- 2026-06-13: Chunk 3 DONE. Installed `/etc/systemd/system/trmnl-calendar.service`, ran `systemctl daemon-reload`, enabled and started the service, and confirmed it is active and listening on `0.0.0.0:8787`.
