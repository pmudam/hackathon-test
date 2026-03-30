from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
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

    def test_filters_incidents_younger_than_two_minutes(self) -> None:
        recent_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
        incidents = [
            {
                "id": "recent-incident",
                "severity": "critical",
                "timestamp": recent_timestamp,
                "service": "piam-preview-dynamodb",
                "detectorName": "PIAM-PREVIEW:Test DynamoDB Read Capacity",
                "description": "Recent incident should be ignored",
            }
        ]

        alerts = incidents_to_alerts(incidents, service_fallback="fallback-service")

        self.assertEqual(alerts, [])

    def test_keeps_incidents_older_than_two_minutes(self) -> None:
        mature_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat().replace("+00:00", "Z")
        incidents = [
            {
                "id": "mature-incident",
                "severity": "critical",
                "timestamp": mature_timestamp,
                "service": "piam-preview-dynamodb",
                "detectorName": "PIAM-PREVIEW:Test DynamoDB Read Capacity",
                "description": "Mature incident should be included",
            }
        ]

        alerts = incidents_to_alerts(incidents, service_fallback="fallback-service")

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["id"], "mature-incident")


if __name__ == "__main__":
    unittest.main()
