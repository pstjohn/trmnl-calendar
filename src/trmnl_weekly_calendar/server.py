from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from threading import RLock
from urllib.parse import urlparse

from trmnl_weekly_calendar.calendar_data import load_events
from trmnl_weekly_calendar.render import days_for_week, render_image, start_of_week


DEFAULT_REFRESH_SECONDS = 15 * 60


@dataclass
class RenderedCalendar:
    bucket: int
    body: bytes
    fingerprint: str
    source: str
    generated_at: datetime


class CalendarCache:
    def __init__(self, refresh_seconds: int) -> None:
        self.refresh_seconds = refresh_seconds
        self._lock = RLock()
        self._rendered: RenderedCalendar | None = None

    def get(self) -> RenderedCalendar:
        bucket = int(time.time() // self.refresh_seconds)
        with self._lock:
            if self._rendered and self._rendered.bucket == bucket:
                return self._rendered

            generated_at = datetime.now()
            week_start = start_of_week(generated_at.date())
            events, all_day_events, source = load_events(week_start)
            image = render_image(
                week_start=week_start,
                days=days_for_week(week_start),
                events=events,
                all_day_events=all_day_events,
                now=generated_at,
            )
            body = encode_image(image)
            digest = hashlib.sha256(body).hexdigest()[:16]
            self._rendered = RenderedCalendar(bucket, body, digest, source, generated_at)
            return self._rendered


def encode_image(image) -> bytes:
    mode = os.environ.get("TRMNL_IMAGE_MODE", "4bit").lower()
    if mode in {"1bit", "bw", "black-white"}:
        image = image.convert("1")
    elif mode in {"gray", "greyscale", "grayscale"}:
        pass
    else:
        image = image.point(lambda p: round(p / 17) * 17)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def make_handler(cache: CalendarCache):
    class TRMNLCalendarHandler(BaseHTTPRequestHandler):
        server_version = "TRMNLWeeklyCalendar/0.1"

        def do_GET(self) -> None:
            self.handle_request(send_body=True)

        def do_HEAD(self) -> None:
            self.handle_request(send_body=False)

        def handle_request(self, *, send_body: bool) -> None:
            path = urlparse(self.path).path
            try:
                if path in {"/", "/healthz"}:
                    self.send_text("ok\n", send_body=send_body)
                elif path == "/trmnl.json":
                    self.send_redirect_json(cache.get(), send_body=send_body)
                elif path in {"/image.png", "/calendar.png"}:
                    self.send_png(cache.get().body, send_body=send_body)
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except Exception as exc:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

        def send_redirect_json(self, rendered: RenderedCalendar, *, send_body: bool) -> None:
            image_url = f"{self.base_url()}/image.png?v={rendered.fingerprint}"
            payload = {
                "filename": f"weekly-calendar-{rendered.fingerprint}",
                "url": image_url,
                "refresh_rate": cache.refresh_seconds,
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if send_body:
                self.wfile.write(body)

        def send_png(self, body: bytes, *, send_body: bool) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", f"public, max-age={cache.refresh_seconds}")
            self.end_headers()
            if send_body:
                self.wfile.write(body)

        def send_text(self, text: str, *, send_body: bool) -> None:
            body = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)

        def base_url(self) -> str:
            configured = os.environ.get("TRMNL_PUBLIC_BASE_URL", "").strip().rstrip("/")
            if configured:
                return configured
            proto = self.headers.get("X-Forwarded-Proto", "http")
            host = self.headers.get("Host", f"localhost:{self.server.server_port}")
            return f"{proto}://{host}"

        def log_message(self, format: str, *args) -> None:
            if os.environ.get("TRMNL_QUIET"):
                return
            super().log_message(format, *args)

    return TRMNLCalendarHandler


def main() -> None:
    host = os.environ.get("TRMNL_HOST", "0.0.0.0")
    port = int(os.environ.get("TRMNL_PORT", "8787"))
    refresh_seconds = int(os.environ.get("TRMNL_REFRESH_SECONDS", str(DEFAULT_REFRESH_SECONDS)))
    cache = CalendarCache(refresh_seconds)
    server = ThreadingHTTPServer((host, port), make_handler(cache))
    print(f"Serving TRMNL weekly calendar on http://{host}:{port}")
    print(f"Redirect JSON: http://{host}:{port}/trmnl.json")
    print(f"Alias image:   http://{host}:{port}/image.png")
    server.serve_forever()


if __name__ == "__main__":
    main()
