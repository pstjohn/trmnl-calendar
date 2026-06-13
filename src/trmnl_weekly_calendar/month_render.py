from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw

from trmnl_weekly_calendar.calendar_data import MonthEvent
from trmnl_weekly_calendar.render import (
    F,
    H,
    W,
    draw_centered,
    draw_hatching,
    ellipsize,
    localize_now,
    rounded_rect,
    start_of_week,
    text_wh,
)


MONTH_WEEK_ROWS = 5


def render_month_image(
    *,
    month_start: date | None = None,
    events: list[MonthEvent] | None = None,
    now: datetime | None = None,
) -> Image.Image:
    local_now = localize_now(now)
    month_start = month_start or local_now.date().replace(day=1)
    events = events or []

    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    margin_x = 58
    top = 46
    title_h = 86
    dow_h = 54
    grid_left = margin_x
    grid_right = W - margin_x
    grid_top = top + title_h + dow_h
    grid_bottom = H - 64
    col_w = (grid_right - grid_left) / 7
    row_h = (grid_bottom - grid_top) / MONTH_WEEK_ROWS
    col_edges = [round(grid_left + i * col_w) for i in range(8)]
    row_edges = [round(grid_top + i * row_h) for i in range(MONTH_WEEK_ROWS + 1)]
    cell_pad = 12

    for y in range(0, H, 7):
        draw.line((0, y, W, y), fill=253, width=1)

    title = month_start.strftime("%B %Y").upper()
    draw.text((grid_left, top + 10), title, font=F["title"], fill=0)
    meta = "MONTH"
    meta_w, meta_h = text_wh(draw, meta, F["meta"])
    draw.text((grid_right - meta_w, top + 31 - meta_h / 2), meta, font=F["meta"], fill=80)
    draw.line((grid_left, top + title_h, grid_right, top + title_h), fill=0, width=2)

    for i, label in enumerate(("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")):
        draw_centered(draw, (col_edges[i], top + title_h, col_edges[i + 1], grid_top), label, F["day"], fill=0)

    first_day = start_of_week(month_start)
    today = local_now.date()
    events_by_day: dict[date, list[MonthEvent]] = defaultdict(list)
    for event in events:
        events_by_day[event.day].append(event)

    for row in range(MONTH_WEEK_ROWS):
        for col in range(7):
            cell_day = first_day + timedelta(days=row * 7 + col)
            x0 = col_edges[col]
            x1 = col_edges[col + 1]
            y0 = row_edges[row]
            y1 = row_edges[row + 1]
            in_month = cell_day.year == month_start.year and cell_day.month == month_start.month
            is_today = cell_day == today

            if not in_month:
                draw.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=251)
            if is_today:
                draw.rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), fill=248)
                draw_hatching(img, (x0 + 2, y0 + 2, x1 - 2, y1 - 2), step=18, fill=230)

            draw.rectangle((x0, y0, x1, y1), outline=216, width=1)
            draw_day_number(draw, cell_day, x0, y0, is_today, in_month)
            draw_month_events(draw, events_by_day.get(cell_day, []), x0, y0, x1, y1, cell_pad)

    return img


def draw_day_number(
    draw: ImageDraw.ImageDraw,
    cell_day: date,
    x0: int,
    y0: int,
    is_today: bool,
    in_month: bool,
) -> None:
    label = str(cell_day.day)
    date_font = F["current"]
    fill = 0 if in_month else 136
    text_x = x0 + 18
    text_y = y0 + 8
    if is_today:
        text_x = x0 + 20
        bbox = draw.textbbox((text_x, text_y), label, font=date_font)
        rounded_rect(draw, (bbox[0] - 9, bbox[1] - 6, bbox[2] + 10, bbox[3] + 9), 3, fill=0)
        draw.text((text_x, text_y), label, font=date_font, fill=255)
        return
    draw.text((text_x, text_y), label, font=date_font, fill=fill)


def draw_month_events(
    draw: ImageDraw.ImageDraw,
    events: list[MonthEvent],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    cell_pad: int,
) -> None:
    if not events:
        return

    event_top = y0 + 52
    row_h = 27
    row_gap = 6
    available_h = y1 - event_top - 14
    max_rows = max(1, int((available_h + row_gap) // (row_h + row_gap)))
    visible = events[:max_rows]
    remaining = len(events) - len(visible)
    if remaining and max_rows > 1:
        visible = events[: max_rows - 1]

    text_x = x0 + cell_pad + 8
    max_w = x1 - text_x - cell_pad - 8
    for i, event in enumerate(visible):
        row_y = event_top + i * (row_h + row_gap)
        rounded_rect(draw, (x0 + cell_pad, row_y, x1 - cell_pad, row_y + row_h), 4, fill=event.tone)
        label = event.title if not event.time_label else f"{event.time_label} {event.title}"
        clipped = ellipsize(draw, label, F["event_small"], max_w)
        _, label_h = text_wh(draw, clipped, F["event_small"])
        draw.text((text_x, row_y + (row_h - label_h) / 2 - 2), clipped, font=F["event_small"], fill=0)

    if remaining:
        more = f"+{remaining + 1} more"
        clipped = ellipsize(draw, more, F["tiny"], max_w)
        row_y = event_top + len(visible) * (row_h + row_gap) + 1
        draw.text((text_x, min(row_y, y1 - 30)), clipped, font=F["tiny"], fill=70)
