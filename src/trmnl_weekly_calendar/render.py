from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, features

try:
    from trmnl_weekly_calendar.png_encode import encode_png_grayscale_4bit, quantize_grayscale_4bit
except ModuleNotFoundError:
    from png_encode import encode_png_grayscale_4bit, quantize_grayscale_4bit


W, H = 1872, 1404
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "outputs"
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
MOCK_WEEK_START = date(2026, 6, 7)

ROBOTO_SERIF = FONT_DIR / "RobotoSerif.ttf"
ROBOTO_FLEX = FONT_DIR / "RobotoFlex.ttf"
CLIMACONS = FONT_DIR / "climacons-webfont.ttf"
LIBERATION_SANS = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
LIBERATION_SANS_BOLD = Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")
DAY_START_HOUR = 6.0
DAY_END_HOUR = 20.0
CURRENT_DAY_FILL = 238
MAX_EVENT_FILL_GRAY = 226


CSS_PX_TO_POINTS = 72 / 96
FONT_LAYOUT_ENGINE = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
VARIATION_WEIGHTS = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Regular": 400,
    "Medium": 500,
    "SemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
    "ExtraBlack": 1000,
}


def axis_name(axis: dict[str, object]) -> str:
    name = axis.get("name", "")
    if isinstance(name, bytes):
        return name.decode("utf-8", "replace")
    return str(name)


def clamp_axis_value(value: float, axis: dict[str, object]) -> float:
    minimum = float(axis["minimum"])
    maximum = float(axis["maximum"])
    return min(maximum, max(minimum, value))


def variation_weight(variation: str | None) -> int | None:
    if not variation:
        return None
    return VARIATION_WEIGHTS.get(variation.removesuffix(" Italic"))


def apply_optical_size(
    loaded: ImageFont.FreeTypeFont,
    size: int,
    variation: str | None,
    optical_size: float | None = None,
) -> None:
    try:
        axes = loaded.get_variation_axes()
    except OSError:
        return

    weight = variation_weight(variation)
    values: list[float] = []
    for axis in axes:
        value = float(axis["default"])
        name = axis_name(axis)
        if name == "Optical Size":
            target_optical_size = optical_size if optical_size is not None else float(size) * CSS_PX_TO_POINTS
            value = clamp_axis_value(target_optical_size, axis)
        elif name == "Weight" and weight is not None:
            value = clamp_axis_value(float(weight), axis)
        values.append(value)

    try:
        loaded.set_variation_by_axes(values)
    except OSError:
        return


def apply_browser_optical_size(loaded: ImageFont.FreeTypeFont, size: int, variation: str | None) -> None:
    apply_optical_size(loaded, size, variation)


def font(
    path: str | Path,
    size: int,
    variation: str | None = None,
    *,
    browser_optical_size: bool = False,
    optical_size: float | None = None,
) -> ImageFont.FreeTypeFont:
    loaded = ImageFont.truetype(str(path), size, layout_engine=FONT_LAYOUT_ENGINE)
    if variation:
        try:
            loaded.set_variation_by_name(variation)
        except OSError:
            pass
    if optical_size is not None:
        apply_optical_size(loaded, size, variation, optical_size)
    elif browser_optical_size:
        apply_browser_optical_size(loaded, size, variation)
    return loaded


def first_existing_font(candidates: tuple[Path, ...], fallback: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return fallback


MONTH_EVENT_FONT = first_existing_font((LIBERATION_SANS,), ROBOTO_FLEX)
MONTH_EVENT_OPTICAL_SIZE = 14 if MONTH_EVENT_FONT == ROBOTO_FLEX else None
MONTH_TIME_FONT = first_existing_font((LIBERATION_SANS_BOLD,), ROBOTO_FLEX)
MONTH_TIME_OPTICAL_SIZE = 14 if MONTH_TIME_FONT == ROBOTO_FLEX else None


F = {
    "title": font(ROBOTO_SERIF, 58, "Bold"),
    "meta": font(ROBOTO_FLEX, 25, "Regular", browser_optical_size=True),
    "day": font(ROBOTO_SERIF, 36, "Bold"),
    "date": font(ROBOTO_SERIF, 31, "Regular"),
    "weather": font(ROBOTO_FLEX, 26, "Regular", browser_optical_size=True),
    "time": font(ROBOTO_SERIF, 27, "Bold"),
    "event": font(ROBOTO_FLEX, 26, "Regular", browser_optical_size=True),
    "event_small": font(ROBOTO_FLEX, 22, "Regular", browser_optical_size=True),
    "current": font(ROBOTO_SERIF, 31, "Bold"),
    "now": font(ROBOTO_FLEX, 22, "Regular", browser_optical_size=True),
    "tiny": font(ROBOTO_FLEX, 20, "Regular", browser_optical_size=True),
    "month_event": font(MONTH_EVENT_FONT, 20, "Regular", optical_size=MONTH_EVENT_OPTICAL_SIZE),
    "month_time": font(MONTH_TIME_FONT, 20, "Bold", optical_size=MONTH_TIME_OPTICAL_SIZE),
    "month_tiny": font(MONTH_EVENT_FONT, 18, "Regular", optical_size=MONTH_EVENT_OPTICAL_SIZE),
}


def configured_zone() -> ZoneInfo:
    return ZoneInfo(os.environ.get("TRMNL_TIMEZONE", "America/Denver"))


def configured_now() -> datetime:
    return datetime.now(configured_zone())


def localize_now(now: datetime | None = None) -> datetime:
    zone = configured_zone()
    if now is None:
        return datetime.now(zone)
    if now.tzinfo is None:
        return now.replace(tzinfo=zone)
    return now.astimezone(zone)


def configured_today() -> date:
    return localize_now().date()


@dataclass
class Event:
    day: int
    start: float
    end: float
    title: str
    where: str = ""
    tone: int = 232


@dataclass
class AllDayEvent:
    start_day: int
    end_day: int
    title: str
    row: int = 0
    tone: int = 238


MOCK_DAYS = [
    ("SUN", "7", "clear", "72 / 51"),
    ("MON", "8", "cloud", "68 / 49"),
    ("TUE", "9", "rain", "61 / 47"),
    ("WED", "10", "partly", "70 / 50"),
    ("THU", "11", "wind", "76 / 54"),
    ("FRI", "12", "clear", "80 / 57"),
    ("SAT", "13", "storm", "73 / 52"),
]

MOCK_ALL_DAY_EVENTS = [
    AllDayEvent(1, 2, "Alex PTO", 0, 238),
    AllDayEvent(3, 3, "Quarterly planning", 0, 232),
    AllDayEvent(3, 3, "School forms due", 1, 244),
    AllDayEvent(4, 4, "Trash + recycling", 0, 244),
    AllDayEvent(5, 6, "Camping prep", 0, 232),
]

MOCK_EVENTS = [
    Event(0, 8.5, 9.5, "Coffee + reading", "Kitchen table", 240),
    Event(0, 16.0, 17.0, "Meal prep", "Home", 235),
    Event(1, 9.0, 10.0, "Weekly planning", "Studio", 232),
    Event(1, 13.0, 14.25, "Product review", "Video", 238),
    Event(1, 17.5, 18.5, "Walk", "Park loop", 242),
    Event(2, 8.0, 9.0, "School dropoff", "", 238),
    Event(2, 10.5, 12.0, "Deep work block", "Desk", 228),
    Event(2, 15.0, 16.0, "Dentist", "Pearl St.", 240),
    Event(3, 7.5, 8.25, "Gym", "", 238),
    Event(3, 11.0, 12.0, "Design critique", "Room 3B", 232),
    Event(3, 18.0, 20.0, "Dinner with Sam", "Northside", 240),
    Event(4, 9.5, 10.25, "1:1 Morgan", "Phone", 235),
    Event(4, 12.0, 13.0, "Lunch outside", "", 244),
    Event(4, 14.0, 16.0, "Prototype pass", "Workshop", 229),
    Event(5, 8.0, 8.75, "Run", "Creek trail", 242),
    Event(5, 10.0, 11.0, "Finance check-in", "Video", 235),
    Event(5, 13.0, 15.0, "Calendar display sketch", "TRMNL", 226),
    Event(5, 19.0, 20.0, "Pick up groceries", "", 241),
    Event(6, 9.0, 10.0, "Farmers market", "Downtown", 238),
    Event(6, 11.5, 13.0, "House projects", "", 234),
    Event(6, 19.0, 21.0, "Movie night", "Living room", 240),
]


def text_wh(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fnt: ImageFont.ImageFont,
    fill: int = 0,
    y_offset: int = 0,
) -> None:
    x0, y0, x1, y1 = box
    tb = draw.textbbox((0, 0), text, font=fnt)
    cx = x0 + (x1 - x0) / 2
    cy = y0 + (y1 - y0) / 2 + y_offset
    draw.text((cx - (tb[0] + tb[2]) / 2, cy - (tb[1] + tb[3]) / 2), text, font=fnt, fill=fill)


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float, float, float],
    radius: int,
    fill: int | None = None,
    outline: int | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(tuple(round(v) for v in xy), radius=radius, fill=fill, outline=outline, width=width)


def event_fill(tone: int) -> int:
    return min(MAX_EVENT_FILL_GRAY, max(0, tone))


def draw_hatching(img: Image.Image, xy: tuple[int, int, int, int], step: int = 11, fill: int = 206) -> None:
    x0, y0, x1, y1 = xy
    w, h = x1 - x0, y1 - y0
    patch = Image.new("L", (w, h), 255)
    mask = Image.new("L", (w, h), 0)
    pdraw = ImageDraw.Draw(patch)
    mdraw = ImageDraw.Draw(mask)
    for x in range(-h, w, step):
        pdraw.line((x, h, x + h, 0), fill=fill, width=1)
        mdraw.line((x, h, x + h, 0), fill=255, width=1)
    img.paste(patch, (x0, y0), mask)


def draw_weather_icon(
    draw: ImageDraw.ImageDraw,
    kind: str,
    cx: int,
    cy: int,
    scale: float = 1.0,
    fill: int = 0,
) -> None:
    glyphs = {
        "clear": "\ue028",  # climacon.sun
        "cloud": "\ue000",  # climacon.cloud
        "rain": "\ue003",  # climacon.rain.cloud
        "partly": "\ue001",  # climacon.cloud.sun
        "wind": "\ue021",  # climacon.wind
        "storm": "\ue025",  # climacon.lightning.cloud
        "snow": "\ue018",  # climacon.snow.cloud
        "fog": "\ue01b",  # climacon.fog.cloud
    }
    glyph = glyphs.get(kind, "\ue000")
    if not CLIMACONS.exists():
        draw_centered(draw, (cx - 42, cy - 34, cx + 42, cy + 34), "?", F["day"], fill=fill)
        return
    icon_font = ImageFont.truetype(str(CLIMACONS), max(18, int(76 * scale)))
    bbox = draw.textbbox((0, 0), glyph, font=icon_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), glyph, font=icon_font, fill=fill)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if text_wh(draw, trial, fnt)[0] <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def ellipsize(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_w: int) -> str:
    if text_wh(draw, text, fnt)[0] <= max_w:
        return text
    while text and text_wh(draw, text + "...", fnt)[0] > max_w:
        text = text[:-1]
    return text.rstrip() + "..."


def short_clock(hour: float) -> str:
    h = int(hour)
    m = int(round((hour - h) * 60))
    if m == 0:
        return str(h % 12 or 12)
    return f"{h % 12 or 12}:{m:02d}"


def time_y(hour: float, top: int, bottom: int) -> float:
    return top + (hour - DAY_START_HOUR) / (DAY_END_HOUR - DAY_START_HOUR) * (bottom - top)


def start_of_week(today: date | None = None, first_weekday: int = 6) -> date:
    """Return the week start for today. Defaults to Sunday-first calendars."""
    today = today or configured_today()
    days_since_start = (today.weekday() - first_weekday) % 7
    return today - timedelta(days=days_since_start)


def days_for_week(week_start: date) -> list[tuple[str, str, str, str]]:
    weather = [("clear", "72 / 51"), ("cloud", "68 / 49"), ("rain", "61 / 47"), ("partly", "70 / 50"), ("wind", "76 / 54"), ("clear", "80 / 57"), ("storm", "73 / 52")]
    days = []
    for i, (kind, temp) in enumerate(weather):
        day = week_start + timedelta(days=i)
        days.append((day.strftime("%a").upper(), str(day.day), kind, temp))
    return days


def allocate_all_day_rows(events: list[AllDayEvent]) -> list[AllDayEvent]:
    occupied_until_by_row: list[int] = []
    allocated: list[AllDayEvent] = []
    for event in sorted(events, key=lambda ev: (ev.start_day, ev.end_day, ev.title)):
        row = 0
        while row < len(occupied_until_by_row) and occupied_until_by_row[row] >= event.start_day:
            row += 1
        if row == len(occupied_until_by_row):
            occupied_until_by_row.append(event.end_day)
        else:
            occupied_until_by_row[row] = event.end_day
        allocated.append(AllDayEvent(event.start_day, event.end_day, event.title, row, event.tone))
    return allocated


def current_marker(week_start: date, now: datetime | None = None) -> tuple[int, float]:
    now = localize_now(now)
    week_end = week_start + timedelta(days=6)
    if week_start <= now.date() <= week_end:
        day = (now.date() - week_start).days
        minutes = now.hour * 60 + now.minute + (1 if now.second >= 30 else 0)
        rounded = round(minutes / 15) * 15
        hour = rounded / 60
    else:
        day = min(6, max(0, (now.date() - week_start).days))
        hour = DAY_START_HOUR
    return day, min(DAY_END_HOUR, max(DAY_START_HOUR, hour))


def render_image(
    *,
    week_start: date = MOCK_WEEK_START,
    days: list[tuple[str, str, str, str]] | None = None,
    all_day_events: list[AllDayEvent] | None = None,
    events: list[Event] | None = None,
    now: datetime | None = None,
) -> Image.Image:
    local_now = localize_now(now)
    days = days or days_for_week(week_start)
    all_day_events = allocate_all_day_rows(all_day_events if all_day_events is not None else MOCK_ALL_DAY_EVENTS)
    events = events if events is not None else MOCK_EVENTS

    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    margin_x = 58
    top = 46
    day_h = 286
    grid_top = top + day_h
    grid_bottom = H - 64
    time_w = 84
    grid_left = margin_x + time_w
    grid_right = W - margin_x
    col_w = (grid_right - grid_left) / 7
    col_edges = [round(grid_left + i * col_w) for i in range(8)]
    card_inset_x = 14
    card_inset_y = 5
    text_pad_x = 20

    # Fine paper grain.
    for y in range(0, H, 7):
        draw.line((0, y, W, y), fill=253, width=1)

    # Day headings with weather tucked beneath each printed date.
    day_top = top
    current_day = local_now.date()
    highlighted_day = (current_day - week_start).days if week_start <= current_day <= week_start + timedelta(days=6) else -1
    for i, (dow, date_label, _kind, _temp) in enumerate(days):
        dow, date_label, kind, temp = days[i]
        x0 = col_edges[i]
        x1 = col_edges[i + 1]
        if i == highlighted_day:
            draw.rectangle((x0 + 2, day_top + 2, x1 - 2, grid_bottom), fill=CURRENT_DAY_FILL)
            rounded_rect(draw, (x0 + 24, day_top + 24, x1 - 24, day_top + 74), 3, fill=0)
            draw_centered(draw, (x0, day_top + 24, x1, day_top + 74), f"{dow} {date_label}", F["day"], fill=255, y_offset=-1)
        else:
            draw_centered(draw, (x0, day_top + 24, x1, day_top + 74), f"{dow} {date_label}", F["day"], fill=0, y_offset=-1)
        draw_weather_icon(draw, kind, round((x0 + x1) / 2), day_top + 122, 0.74)
        draw_centered(draw, (x0, day_top + 165, x1, day_top + 198), temp, F["weather"], fill=0)

    # All-day event band.
    all_day_top = day_top + 212
    row_h = 34
    row_gap = 6
    for all_day in all_day_events:
        x0 = col_edges[all_day.start_day] + card_inset_x
        x1 = col_edges[all_day.end_day + 1] - card_inset_x
        y0 = all_day_top + all_day.row * (row_h + row_gap)
        y1 = y0 + row_h
        rounded_rect(draw, (x0, y0, x1, y1), 5, fill=event_fill(all_day.tone))
        label = ellipsize(draw, all_day.title, F["event"], round(x1 - x0 - text_pad_x))
        _, lh = text_wh(draw, label, F["event"])
        draw.text((x0 + text_pad_x / 2, y0 + (row_h - lh) / 2 - 2), label, font=F["event"], fill=0)
    # Time grid.
    for hour in range(int(DAY_START_HOUR), int(DAY_END_HOUR) + 1):
        y = round(time_y(hour, grid_top, grid_bottom))
        label = f"{hour % 12 or 12}{'a' if hour < 12 else 'p'}"
        tw, th = text_wh(draw, label, F["time"])
        draw.text((grid_left - 18 - tw, y - th / 2 - 2), label, font=F["time"], fill=0)

    # Events.
    for ev in sorted(events, key=lambda event: (event.day, event.start, event.end, event.title)):
        visible_start = max(DAY_START_HOUR, ev.start)
        visible_end = min(DAY_END_HOUR, ev.end)
        if visible_end <= DAY_START_HOUR or visible_start >= DAY_END_HOUR or visible_end <= visible_start:
            continue

        x0 = col_edges[ev.day] + card_inset_x
        x1 = col_edges[ev.day + 1] - card_inset_x
        y0 = time_y(visible_start, grid_top, grid_bottom) + card_inset_y
        y1 = time_y(visible_end, grid_top, grid_bottom) - card_inset_y
        if y1 - y0 < 34:
            y0 = max(grid_top + card_inset_y, y1 - 34)
        rounded_rect(draw, (x0, y0, x1, y1), 5, fill=event_fill(ev.tone))
        start_h = int(visible_start)
        start_m = int(round((visible_start - start_h) * 60))
        end_h = int(visible_end)
        end_m = int(round((visible_end - end_h) * 60))
        time_text = f"{start_h % 12 or 12}:{start_m:02d}-{end_h % 12 or 12}:{end_m:02d}"
        tx = x0 + text_pad_x
        max_w = round(x1 - tx - text_pad_x)
        box_h = y1 - y0
        if box_h < 68:
            compact_time = f"{short_clock(visible_start)}-{short_clock(visible_end)}"
            compact = f"{compact_time} {ev.title}"
            line = ellipsize(draw, compact, F["event_small"], max_w)
            _, lh = text_wh(draw, line, F["event_small"])
            draw.text((tx, y0 + (box_h - lh) / 2 - 2), line, font=F["event_small"], fill=0)
        else:
            ty = y0 + 8
            draw.text((tx, ty), time_text, font=F["event_small"], fill=0)
            ty += 25
            for line in wrap(draw, ev.title, F["event"], max_w)[:2]:
                draw.text((tx, ty), line, font=F["event"], fill=0)
                ty += 28
            if ev.where and y1 - ty > 22:
                location = ellipsize(draw, ev.where, F["event_small"], max_w)
                draw.text((tx, ty + 1), location, font=F["event_small"], fill=70)

    marker_day, marker_hour = current_marker(week_start, local_now)
    marker_y = round(time_y(marker_hour, grid_top, grid_bottom))
    marker_x0 = col_edges[marker_day] + card_inset_x
    marker_x1 = col_edges[marker_day + 1] - card_inset_x
    marker_mid = round((marker_x0 + marker_x1) / 2)
    draw.line((marker_x0 + 8, marker_y, marker_mid - 16, marker_y), fill=0, width=2)
    draw.line((marker_mid + 16, marker_y, marker_x1 - 8, marker_y), fill=0, width=2)
    draw.ellipse((marker_mid - 6, marker_y - 6, marker_mid + 6, marker_y + 6), fill=255, outline=0, width=2)
    draw.ellipse((marker_mid - 2, marker_y - 2, marker_mid + 2, marker_y + 2), fill=0)
    for direction in (-1, 1):
        tip = marker_x0 + 2 if direction < 0 else marker_x1 - 2
        inner = tip + direction * 18
        wing = 7
        draw.polygon(
            [
                (tip, marker_y),
                (inner, marker_y - wing),
                (inner - direction * 4, marker_y),
                (inner, marker_y + wing),
            ],
            fill=0,
        )
    return img


def write_outputs(img: Image.Image) -> tuple[Path, Path, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    gray_path = OUT / "trmnl_weekly_calendar_mockup_grayscale.png"
    gray4_path = OUT / "trmnl_weekly_calendar_mockup_4bit_grayscale.png"
    bw_path = OUT / "trmnl_weekly_calendar_mockup_dithered.png"
    img.save(gray_path)
    gray4 = quantize_grayscale_4bit(img)
    gray4_path.write_bytes(encode_png_grayscale_4bit(gray4))
    bw = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    bw.save(bw_path)
    return gray_path, gray4_path, bw_path


def render() -> None:
    paths = write_outputs(render_image())
    for path in paths:
        print(path)


if __name__ == "__main__":
    render()
