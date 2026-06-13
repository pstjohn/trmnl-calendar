from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from trmnl_weekly_calendar import server


class ServerRenderTests(unittest.TestCase):
    def test_weekly_render_starts_on_generated_date(self) -> None:
        captured = {}
        generated_at = datetime(2026, 6, 13, 9, 30, tzinfo=ZoneInfo("America/Denver"))

        def fake_render_image(**kwargs):
            captured.update(kwargs)
            return object()

        with patch.object(server, "load_events", return_value=([], [], "calendar")) as load_events:
            with patch.object(server, "load_weekly_weather", return_value=(None, "weather")) as load_weather:
                with patch.object(server, "render_image", fake_render_image):
                    image, source = server.render_weekly(generated_at)

        self.assertIsNotNone(image)
        self.assertEqual(source, "calendar+weather")
        self.assertEqual(load_events.call_args.args[0].isoformat(), "2026-06-13")
        self.assertEqual(load_weather.call_args.args[0].isoformat(), "2026-06-13")
        self.assertEqual(captured["week_start"].isoformat(), "2026-06-13")
        self.assertEqual(captured["days"][0][:2], ("SAT", "13"))
        self.assertEqual(captured["days"][-1][:2], ("FRI", "19"))


if __name__ == "__main__":
    unittest.main()
