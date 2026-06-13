from __future__ import annotations

import json
import os
import shlex
import subprocess
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from trmnl_weekly_calendar.render import AllDayEvent, Event, MOCK_ALL_DAY_EVENTS, MOCK_EVENTS


TONE_STEPS = [238, 232, 240, 235, 242, 228, 244, 229, 226, 241, 234]


def load_events(week_start: date) -> tuple[list[Event], list[AllDayEvent], str]:
    command_template = os.environ.get("TRMNL_GOG_COMMAND", "").strip()
    if not command_template:
        return MOCK_EVENTS, MOCK_ALL_DAY_EVENTS, "mock"

    payload = run_gog(command_template, week_start)
    raw_events = extract_event_list(payload)
    events, all_day_events = parse_events(raw_events, week_start, local_zone())
    return events, all_day_events, "gog"


def run_gog(command_template: str, week_start: date) -> Any:
    end = week_start + timedelta(days=7)
    values = {
        "start": week_start.isoformat(),
        "end": end.isoformat(),
        "start_datetime": datetime.combine(week_start, time.min).isoformat(),
        "end_datetime": datetime.combine(end, time.min).isoformat(),
    }
    command = shlex.split(command_template.format(**values))
    result = subprocess.run(command, capture_output=True, check=True, text=True, timeout=30)
    return json.loads(result.stdout)


def extract_event_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("items", "events", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    flattened: list[dict[str, Any]] = []
    for value in payload.values():
        if isinstance(value, list):
            flattened.extend(item for item in value if isinstance(item, dict) and has_event_time(item))
    return flattened


def parse_events(raw_events: list[dict[str, Any]], week_start: date, tz: ZoneInfo) -> tuple[list[Event], list[AllDayEvent]]:
    timed: list[Event] = []
    all_day: list[AllDayEvent] = []
    week_end = week_start + timedelta(days=7)

    for index, raw in enumerate(raw_events):
        title = clean_text(raw.get("summary") or raw.get("title") or raw.get("name") or "Untitled")
        location = clean_text(raw.get("location") or raw.get("where") or "")
        start_value = first_value(raw, "start", "startTime", "start_time", "starts_at", "begin")
        end_value = first_value(raw, "end", "endTime", "end_time", "ends_at", "finish")
        if start_value is None:
            continue

        start, start_is_all_day = parse_temporal(start_value, tz)
        end, end_is_all_day = parse_temporal(end_value, tz) if end_value is not None else (start, start_is_all_day)
        tone = TONE_STEPS[index % len(TONE_STEPS)]

        if start_is_all_day or end_is_all_day:
            start_day = start if isinstance(start, date) and not isinstance(start, datetime) else start.date()
            end_day = end if isinstance(end, date) and not isinstance(end, datetime) else end.date()
            inclusive_end = end_day - timedelta(days=1) if end_day > start_day else start_day
            clipped_start = max(start_day, week_start)
            clipped_end = min(inclusive_end, week_end - timedelta(days=1))
            if clipped_start <= clipped_end:
                all_day.append(
                    AllDayEvent(
                        (clipped_start - week_start).days,
                        (clipped_end - week_start).days,
                        title,
                        tone=tone,
                    )
                )
            continue

        start_dt = ensure_datetime(start, tz)
        end_dt = ensure_datetime(end, tz)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=30)
        for day_offset in range(7):
            day = week_start + timedelta(days=day_offset)
            day_start = datetime.combine(day, time.min, tz)
            day_end = day_start + timedelta(days=1)
            segment_start = max(start_dt, day_start)
            segment_end = min(end_dt, day_end)
            if segment_start >= segment_end:
                continue
            start_hour = max(6.0, hour_float(segment_start))
            raw_end_hour = 24.0 if segment_end == day_end else hour_float(segment_end)
            end_hour = min(22.0, raw_end_hour)
            if end_hour <= 6.0 or start_hour >= 22.0:
                continue
            timed.append(Event(day_offset, start_hour, max(start_hour + 0.25, end_hour), title, location, tone))

    return timed, all_day


def first_value(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw:
            return raw[key]
    return None


def has_event_time(raw: dict[str, Any]) -> bool:
    return any(key in raw for key in ("start", "startTime", "start_time", "starts_at", "begin"))


def parse_temporal(value: Any, tz: ZoneInfo) -> tuple[datetime | date, bool]:
    if isinstance(value, dict):
        if value.get("date"):
            return date.fromisoformat(str(value["date"])), True
        for key in ("dateTime", "datetime", "time"):
            if value.get(key):
                return parse_datetime(str(value[key]), tz), False

    if isinstance(value, str):
        if "T" not in value and len(value) == 10:
            return date.fromisoformat(value), True
        return parse_datetime(value, tz), False

    raise ValueError(f"Unsupported calendar timestamp: {value!r}")


def parse_datetime(value: str, tz: ZoneInfo) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def ensure_datetime(value: datetime | date, tz: ZoneInfo) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min, tz)


def hour_float(value: datetime) -> float:
    return value.hour + value.minute / 60 + value.second / 3600


def local_zone() -> ZoneInfo:
    return ZoneInfo(os.environ.get("TRMNL_TIMEZONE", "America/Denver"))


def clean_text(value: Any) -> str:
    return " ".join(str(value).split())
