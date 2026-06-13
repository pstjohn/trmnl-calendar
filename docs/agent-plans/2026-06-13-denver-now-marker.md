# Denver Now Marker Plan

## Goal

Render the weekly calendar's current-day highlight and "now" marker using Mountain time, specifically `America/Denver`, instead of the machine's UTC clock.

## Constraints

- Keep `TRMNL_TIMEZONE` as the configured timezone source.
- Preserve existing event parsing, week layout, and marker rendering geometry.
- Restart the running service so public endpoints pick up the change.
- Avoid new third-party dependencies.

## Discovered Context

- The systemd service already sets `TRMNL_TIMEZONE=America/Denver`.
- `calendar_data.py` parses event times with `ZoneInfo(os.environ.get("TRMNL_TIMEZONE", "America/Denver"))`.
- `server.py` currently uses naive `datetime.now()`, which follows the host clock timezone.
- `render.py` also uses naive `datetime.now()` and `date.today()` for fallback current marker and highlight calculations.
- The host/system journal timestamps are UTC, while the user expects the rendered marker to show local Mountain time.

## Alternatives Considered

- Set the whole systemd service `TZ=America/Denver`.
  - Simple, but relies on process-global timezone behavior and does not fix direct renderer invocation.
- Only pass a Denver-aware `now` from `server.py`.
  - Fixes the deployed service, but leaves CLI/default rendering inconsistent.
- Add small timezone helpers in the renderer and use them from both renderer fallbacks and the server.
  - Keeps behavior explicit, uses existing `TRMNL_TIMEZONE`, and fixes both service and direct rendering. This is the selected approach.

## Final Design

Add renderer helpers for configured timezone, current datetime, and current date. Use those helpers in `start_of_week`, `current_marker`, and `render_image` fallback paths. Update `server.py` to call the configured current datetime helper instead of naive `datetime.now()`.

## Chunk List

### Chunk 1: Timezone-Aware Now Source

- Objective: Make server and renderer current-time calculations use `TRMNL_TIMEZONE`.
- Files or areas likely to change: `src/trmnl_weekly_calendar/render.py`, `src/trmnl_weekly_calendar/server.py`.
- Dependencies on other chunks: none.
- Non-goals: changing event parsing or service unit configuration.
- Commands to run: `uv run python -m compileall src`; run a small `TRMNL_TIMEZONE=America/Denver` script that prints configured local time and marker hour.
- Expected checks: configured current time reports an `America/Denver` tzinfo and marker calculations use the local hour.
- Blocker-report format: failing command, traceback, and expected vs actual timezone/hour.

### Chunk 2: Restart And Verify

- Objective: Restart the local service and verify public/local endpoints serve the updated image.
- Files or areas likely to change: none.
- Dependencies on other chunks: Chunk 1.
- Non-goals: changing Brev exposure or systemd unit.
- Commands to run: `sudo systemctl restart trmnl-calendar.service`; `curl /trmnl.json`; `curl /image.png`.
- Expected checks: service active, `/trmnl.json` returns refresh rate 900, `/image.png` returns PNG.
- Blocker-report format: failed command, systemctl status excerpt, and journal excerpt.

## Subagent Packets

- Not needed for this small targeted fix.

## Acceptance Criteria

- The server passes a timezone-aware `America/Denver` timestamp into `render_image`.
- Renderer fallback marker/highlight calculations use `TRMNL_TIMEZONE`.
- Renderer compiles.
- The service restarts and serves a PNG with a new fingerprint.

## Test Plan

- Run `uv run python -m compileall src`.
- Run a script with `TRMNL_TIMEZONE=America/Denver` to inspect configured local time and marker hour.
- Restart `trmnl-calendar.service`.
- Verify local/public `/trmnl.json` and `/image.png`.

## Linear Links

- Not configured.

## Progress Log

- 2026-06-13: Inspected server and renderer; found naive `datetime.now()`/`date.today()` paths despite `TRMNL_TIMEZONE=America/Denver` being configured in the service.
