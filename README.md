# TRMNL Weekly Calendar

A small Python renderer and TRMNL Redirect/Alias server for a `1872 x 1404` TRMNL X weekly calendar.

The current design uses:

- Roboto Serif for day headings and the left time rail
- Roboto Flex for body text, events, all-day events, and temperatures
- Climacons for weather icons
- True 4-bit grayscale PNG output for TRMNL X

## Render

From this project directory with `uv`:

```bash
uv sync
uv run render-trmnl-calendar
```

Or with an already prepared Python environment:

```bash
python3 src/trmnl_weekly_calendar/render.py
```

The main TRMNL output is a grayscale PNG with bit depth `4`, color type `0`, and 16 gray levels:

```text
outputs/trmnl_weekly_calendar_mockup_4bit_grayscale.png
```

The script also writes a continuous 8-bit grayscale preview and a 1-bit dithered comparison image.

## TRMNL Plugin Server

Use the Redirect plugin for the real calendar. Redirect lets this server return a stable image URL plus a `refresh_rate` of 900 seconds, and it lets the `filename` change only when the generated image changes. That avoids unnecessary redraws while still checking every 15 minutes.

Alias can also work if you only want TRMNL to fetch `/image.png` directly, but Redirect is a better fit for a dynamic calendar because the JSON response controls refresh cadence and cache diffing.

Install and run with `uv`:

```bash
uv sync
uv run serve-trmnl-calendar
```

Or install and run with `pip`:

```bash
python3 -m pip install -e .
serve-trmnl-calendar
```

The server exposes:

```text
GET /weekly/trmnl.json  Weekly Redirect plugin JSON
GET /weekly/image.png   Weekly PNG image for Redirect or Alias
GET /month/trmnl.json   Month Redirect plugin JSON
GET /month/image.png    Month PNG image for Redirect or Alias
GET /trmnl.json         Legacy weekly Redirect plugin JSON
GET /image.png          Legacy weekly PNG image
GET /healthz            Health check
```

By default, the server renders the mock events. Set `TRMNL_GOG_COMMAND` to fetch live Google Calendar JSON with `gog`. The command is a template; `{start}` is the week start date and `{end}` is the exclusive week end date.

```bash
export GOG_ACCOUNT='you@example.com'
export TRMNL_GOG_COMMAND='gog calendar events primary --account {account} --from {start} --to {end} --json --no-input'
export TRMNL_PUBLIC_BASE_URL='https://your-public-host.example.com'
serve-trmnl-calendar
```

Adjust the `gog` arguments to match the CLI you use. The command template supports `{start}`, `{end}`, `{start_datetime}`, `{end_datetime}`, and `{account}` from `GOG_ACCOUNT`.

For the local Hermes setup, use:

```bash
export TRMNL_GOG_COMMAND='gog calendar events primary --account {account} --from {start} --to {end} --all-pages --json --no-input'
```

The parser accepts common Google Calendar shapes such as top-level arrays, `items`, `events`, or `data`, with `summary`, `location`, `start.dateTime`, `start.date`, `end.dateTime`, and `end.date`.

Useful environment variables:

```text
TRMNL_HOST=0.0.0.0
TRMNL_PORT=8787
TRMNL_PUBLIC_BASE_URL=https://your-public-host.example.com
TRMNL_REFRESH_SECONDS=900
TRMNL_CALENDAR_DATA_TTL_SECONDS=7200
TRMNL_TIMEZONE=America/Denver
TRMNL_IMAGE_MODE=4bit
```

`TRMNL_IMAGE_MODE=4bit` writes a packed PNG with bit depth `4` and grayscale color type `0`.

For TRMNL Redirect, configure the plugin Web Address to:

```text
https://your-public-host.example.com/weekly/trmnl.json
https://your-public-host.example.com/month/trmnl.json
```

For Alias testing, configure the Image URL to:

```text
http://your-local-or-public-host:8787/image.png
```

## Structure

```text
assets/fonts/                 Vendored fonts used by the renderer
outputs/                      Generated mockups
src/trmnl_weekly_calendar/    Rendering code
```

## Notes

The mock data is still embedded in `src/trmnl_weekly_calendar/render.py` so design iterations can stay fast and visual. Live calendar parsing lives in `src/trmnl_weekly_calendar/calendar_data.py`, and the TRMNL HTTP routes live in `src/trmnl_weekly_calendar/server.py`.
