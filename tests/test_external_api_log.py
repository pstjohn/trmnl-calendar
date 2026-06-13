from __future__ import annotations

import os
import subprocess
import unittest
from datetime import date
from unittest.mock import patch

from trmnl_weekly_calendar import calendar_data
from trmnl_weekly_calendar.external_api_log import log_http_call, sanitized_url_parts, stable_fingerprint


class ExternalApiLogTests(unittest.TestCase):
    def test_sanitized_url_parts_removes_query_and_redacts_point_coordinates(self) -> None:
        host, path = sanitized_url_parts("https://api.weather.gov/points/39.772,-105.231?private=value")

        self.assertEqual(host, "api.weather.gov")
        self.assertEqual(path, "/points/<coords>")

    def test_http_call_log_omits_query_string(self) -> None:
        with patch.dict(os.environ, {"TRMNL_EXTERNAL_API_LOGGING": "1"}):
            with self.assertLogs("trmnl_weekly_calendar.external_api", level="INFO") as logs:
                log_http_call(
                    provider="open-meteo",
                    url="https://api.open-meteo.com/v1/forecast?latitude=39.772&longitude=-105.231",
                    status=200,
                    duration_ms=12,
                    bytes_read=256,
                )

        line = logs.output[0]
        self.assertIn("provider=open-meteo", line)
        self.assertIn("host=api.open-meteo.com", line)
        self.assertIn("path=/v1/forecast", line)
        self.assertNotIn("latitude", line)
        self.assertNotIn("39.772", line)

    def test_gog_call_log_uses_calendar_fingerprint(self) -> None:
        result = subprocess.CompletedProcess(["gog"], 0, stdout="[]", stderr="")

        with patch.dict(os.environ, {"TRMNL_EXTERNAL_API_LOGGING": "1"}, clear=True):
            with patch.object(calendar_data.subprocess, "run", return_value=result):
                with self.assertLogs("trmnl_weekly_calendar.external_api", level="INFO") as logs:
                    payload = calendar_data.run_gog(
                        "gog calendar events {calendar} --from {start} --to {end}",
                        date(2026, 6, 13),
                        date(2026, 6, 20),
                        "private-calendar-id",
                    )

        self.assertEqual(payload, [])
        line = logs.output[0]
        self.assertIn(f"calendar={stable_fingerprint('private-calendar-id')}", line)
        self.assertIn("range_start=2026-06-13", line)
        self.assertNotIn("private-calendar-id", line)


if __name__ == "__main__":
    unittest.main()
