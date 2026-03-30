from __future__ import annotations

import json
import unittest
from pathlib import Path

from rca_assistant.engine import RootCauseEngine


class RootCauseEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RootCauseEngine(correlation_window_minutes=90)
        base = Path(__file__).resolve().parent.parent / "data"
        with (base / "sample_splunk_alerts.json").open("r", encoding="utf-8") as sp:
            self.splunk_alerts = json.load(sp)

    def test_detects_api_failure_from_splunk_alerts(self) -> None:
        finding = self.engine.analyze(self.splunk_alerts)

        self.assertTrue(
            any(token in finding.probable_root_cause.lower() for token in ["memory", "api"]),
            msg=f"Unexpected probable cause: {finding.probable_root_cause}",
        )
        self.assertGreaterEqual(finding.confidence, 0.35)
        self.assertTrue(
            any(
                token in " ".join(finding.remediation_steps).lower()
                for token in ["endpoint", "retries", "memory", "profil"]
            )
        )

    def test_fallback_for_single_cpu_alert(self) -> None:
        cpu_only = [
            {
                "id": "cw-x",
                "timestamp": "2026-03-23T11:00:00Z",
                "service": "inventory-api",
                "severity": "critical",
                "category": "cpu",
                "title": "CPU high",
                "message": "CPU saturation alert",
                "metadata": {"metric_name": "CPUUtilization", "metric_value": 91},
            }
        ]
        finding = self.engine.analyze(cpu_only)

        self.assertIn("cpu", finding.probable_root_cause.lower())
        self.assertGreater(finding.confidence, 0.3)


if __name__ == "__main__":
    unittest.main()
