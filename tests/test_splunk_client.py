from __future__ import annotations

import json
import unittest
from pathlib import Path

from rca_assistant.splunk_client import incidents_to_alerts


class SplunkClientTests(unittest.TestCase):
    def setUp(self) -> None:
        base = Path(__file__).resolve().parent.parent / "data"
        self.incidents = json.loads((base / "sample_splunk_incidents.json").read_text(encoding="utf-8"))

    def test_incident_normalization(self) -> None:
        alerts = incidents_to_alerts(self.incidents, service_fallback="fallback-service")

        self.assertEqual(len(alerts), 2)
        self.assertTrue(all(alert["service"] == "piam-preview-dynamodb" for alert in alerts))
        self.assertEqual(alerts[0]["severity"], "critical")
        self.assertEqual(alerts[1]["severity"], "high")
        self.assertTrue(all("source" in alert["metadata"] for alert in alerts))
        self.assertTrue(all(alert["timestamp"].endswith("Z") for alert in alerts))


if __name__ == "__main__":
    unittest.main()
