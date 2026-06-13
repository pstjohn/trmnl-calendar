# Event Location Overflow Plan

## Goal

Prevent event location/address text from overflowing its event box in the TRMNL weekly calendar render.

## Constraints

- Keep the current visual layout and event card sizing.
- Preserve existing title wrapping and compact-event behavior.
- Avoid adding new dependencies.
- Restart the local systemd service after the renderer change so public endpoints use the fix.

## Discovered Context

- Timed event cards are rendered in `src/trmnl_weekly_calendar/render.py`.
- Event titles are wrapped with `wrap(...)[:2]`.
- All-day titles are bounded with `ellipsize(...)`.
- Timed event location text currently draws `ev.where` directly at line 358, with no width cap or clipping.
- No repo test suite exists.

## Alternatives Considered

- Clip the whole event card with an image mask.
  - Strong containment, but more invasive and risks clipping rounded corners or current marker art.
- Wrap locations across multiple lines.
  - More readable for addresses, but competes with title space in short events.
- Ellipsize the location line to the event text width.
  - Minimal, consistent with all-day events, and directly fixes horizontal overflow. This is the selected approach.

## Final Design

Use the existing `ellipsize` helper before drawing `ev.where`, using the same `max_w` calculated for event titles. Only draw the location if the resulting label is non-empty and there is vertical room, preserving the current one-line location treatment.

## Chunk List

### Chunk 1: Bound Location Text

- Objective: Replace raw location drawing with width-bounded location text.
- Files or areas likely to change: `src/trmnl_weekly_calendar/render.py`.
- Dependencies on other chunks: none.
- Non-goals: redesign event cards, change calendar data parsing, or adjust title wrapping.
- Commands to run: `uv run python -m compileall src`; render a sample with long location text.
- Expected checks: location drawing uses `max_w` and long location text no longer spills horizontally.
- Blocker-report format: file, failing command, and traceback or rendered-output concern.

### Chunk 2: Restart And Verify Service

- Objective: Restart the local service and verify public/local endpoints still return the updated image.
- Files or areas likely to change: none.
- Dependencies on other chunks: Chunk 1.
- Non-goals: change systemd unit configuration.
- Commands to run: `sudo systemctl restart trmnl-calendar.service`, `curl /trmnl.json`, `curl /image.png`.
- Expected checks: service active, image endpoint returns PNG.
- Blocker-report format: failed command, service status, and journal excerpt.

## Subagent Packets

- Not needed for this small targeted fix.

## Acceptance Criteria

- Long event locations are ellipsized within the event card width.
- Existing compact events still render as before.
- Renderer compiles.
- Local service restarts and serves a PNG.

## Test Plan

- Run `uv run python -m compileall src`.
- Render a synthetic event with a long address/location.
- Restart `trmnl-calendar.service`.
- Verify `http://127.0.0.1:8787/trmnl.json` and `/image.png`.

## Linear Links

- Not configured.

## Progress Log

- 2026-06-13: Inspected renderer and confirmed raw `ev.where` drawing is the horizontal overflow source.
- 2026-06-13: Chunk 1 DONE. Replaced raw location drawing with `ellipsize(...)`, ran `uv run python -m compileall src`, and rendered a synthetic long-address sample that measured within the event text width.
- 2026-06-13: Chunk 2 DONE. Restarted `trmnl-calendar.service`, confirmed it is active, and verified local/public `/trmnl.json` plus cache-busted `/image.png` responses.
- 2026-06-13: Final review DONE. Reran compile, long-address render measurement, service status, and local endpoint checks; no findings.
