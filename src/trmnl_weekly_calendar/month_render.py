from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw

from trmnl_weekly_calendar.calendar_data import MonthEvent
from trmnl_weekly_calendar.render import (
    CURRENT_DAY_FILL,
    F,
    H,
    W,
    draw_centered,
    ellipsize,
    event_fill,
    localize_now,
    rounded_rect,
    start_of_week,
    text_wh,
    wrap,
)


MONTH_WEEK_ROWS = 5
MONTH_EVENT_ROW_H = 27
MONTH_EVENT_ROW_GAP = 6
MONTH_EVENT_LINE_STEP = 20
MONTH_EVENT_MAX_LINES = 3
MONTH_EVENT_TOP_OFFSET = 52
MONTH_TODAY_EVENT_TOP_OFFSET = 58


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
                draw.rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), fill=CURRENT_DAY_FILL)

            draw_day_number(draw, cell_day, x0, y0, is_today, in_month)
            draw_month_events(draw, events_by_day.get(cell_day, []), x0, y0, x1, y1, cell_pad, is_today)

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
        rounded_rect(draw, (bbox[0] - 7, bbox[1] - 4, bbox[2] + 8, bbox[3] + 6), 3, fill=0)
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
    is_today: bool = False,
) -> None:
    if not events:
        return

    event_top = y0 + (MONTH_TODAY_EVENT_TOP_OFFSET if is_today else MONTH_EVENT_TOP_OFFSET)
    available_h = y1 - event_top - 14
    max_rows = max(1, int((available_h + MONTH_EVENT_ROW_GAP) // (MONTH_EVENT_ROW_H + MONTH_EVENT_ROW_GAP)))
    visible = events[:max_rows]
    hidden_count = len(events) - len(visible)
    if hidden_count and max_rows > 1:
        visible = events[: max_rows - 1]
        hidden_count = len(events) - len(visible)

    text_x = x0 + cell_pad + 8
    max_w = x1 - text_x - cell_pad - 8
    labels = [event.title if not event.time_label else f"{event.time_label} {event.title}" for event in visible]
    line_counts = month_event_line_counts(draw, labels, max_w, available_h, bool(hidden_count))

    row_y = event_top
    for event, label, line_count in zip(visible, labels, line_counts):
        row_h = month_event_row_height(line_count)
        rounded_rect(
            draw,
            (x0 + cell_pad, row_y, x1 - cell_pad, row_y + row_h),
            4,
            fill=event_fill(event.tone),
        )
        lines = month_event_lines(draw, label, max_w, line_count)
        lines_h = line_count * MONTH_EVENT_LINE_STEP
        text_y = row_y + (row_h - lines_h) / 2
        for line in lines:
            draw.text((text_x, text_y - 2), line, font=F["month_event"], fill=0)
            text_y += MONTH_EVENT_LINE_STEP
        row_y += row_h + MONTH_EVENT_ROW_GAP

    if hidden_count:
        more = f"+{hidden_count} more"
        clipped = ellipsize(draw, more, F["month_tiny"], max_w)
        draw.text((text_x, min(row_y + 1, y1 - 30)), clipped, font=F["month_tiny"], fill=70)


def month_event_line_counts(
    draw: ImageDraw.ImageDraw,
    labels: list[str],
    max_w: int,
    available_h: float,
    has_more: bool,
) -> list[int]:
    line_counts = [1 for _label in labels]
    more_h = MONTH_EVENT_ROW_H + MONTH_EVENT_ROW_GAP if has_more else 0
    used_h = month_events_height(line_counts) + more_h
    spare_h = available_h - used_h
    if spare_h < MONTH_EVENT_LINE_STEP:
        return line_counts

    for index, label in enumerate(labels):
        if text_wh(draw, label, F["month_event"])[0] <= max_w:
            continue
        wrapped = wrap(draw, label, F["month_event"], max_w)
        target_lines = min(MONTH_EVENT_MAX_LINES, max(1, len(wrapped)))
        while line_counts[index] < target_lines and spare_h >= MONTH_EVENT_LINE_STEP:
            line_counts[index] += 1
            spare_h -= MONTH_EVENT_LINE_STEP
    return line_counts


def month_events_height(line_counts: list[int]) -> int:
    if not line_counts:
        return 0
    return sum(month_event_row_height(line_count) for line_count in line_counts) + MONTH_EVENT_ROW_GAP * (len(line_counts) - 1)


def month_event_row_height(line_count: int) -> int:
    return MONTH_EVENT_ROW_H + (line_count - 1) * MONTH_EVENT_LINE_STEP


def month_event_lines(draw: ImageDraw.ImageDraw, label: str, max_w: int, max_lines: int) -> list[str]:
    if max_lines <= 1:
        return [ellipsize(draw, label, F["month_event"], max_w)]

    lines = wrap(draw, label, F["month_event"], max_w)
    if len(lines) <= max_lines:
        return lines

    clipped = lines[:max_lines]
    clipped[-1] = ellipsize(draw, " ".join(lines[max_lines - 1 :]), F["month_event"], max_w)
    return clipped
