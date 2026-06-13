from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


LOGGER = logging.getLogger("trmnl_weekly_calendar.external_api")


def external_api_logging_enabled() -> bool:
    value = os.environ.get("TRMNL_EXTERNAL_API_LOGGING", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def perf_counter() -> float:
    return time.perf_counter()


def duration_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1000)


def log_http_call(
    *,
    provider: str,
    url: str,
    status: int | str,
    duration_ms: int,
    bytes_read: int | None = None,
    error: str | None = None,
) -> None:
    if not should_log_external_api_call():
        return

    host, path = sanitized_url_parts(url)
    LOGGER.info(
        "external_api_call kind=http provider=%s host=%s path=%s status=%s duration_ms=%d bytes=%s error=%s",
        provider,
        host,
        path,
        status,
        duration_ms,
        "-" if bytes_read is None else bytes_read,
        error or "-",
    )


def log_subprocess_call(
    *,
    provider: str,
    command: list[str],
    operation: str,
    status: int | str,
    duration_ms: int,
    error: str | None = None,
    **fields: Any,
) -> None:
    if not should_log_external_api_call():
        return

    command_name = Path(command[0]).name if command else "-"
    field_text = " ".join(f"{key}={value}" for key, value in fields.items())
    if field_text:
        field_text = f" {field_text}"
    LOGGER.info(
        "external_api_call kind=subprocess provider=%s command=%s operation=%s status=%s duration_ms=%d error=%s%s",
        provider,
        command_name,
        operation,
        status,
        duration_ms,
        error or "-",
        field_text,
    )


def should_log_external_api_call() -> bool:
    return external_api_logging_enabled() and LOGGER.isEnabledFor(logging.INFO)


def sanitized_url_parts(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    path = re.sub(r"^/points/-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", "/points/<coords>", path)
    return parsed.netloc or "-", path


def stable_fingerprint(value: str | None) -> str:
    if not value:
        return "none"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
