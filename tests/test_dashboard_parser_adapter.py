from __future__ import annotations

import json
import unittest
from pathlib import Path

from rca_assistant.dashboard_adapter import evaluate_dashboard_policy
from rca_assistant.dashboard_parser import parse_dashboard_dsl
from rca_assistant.engine import RootCauseEngine


class DashboardParserAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        base = Path(__file__).resolve().parent.parent / "data"
        self.dsl_text = (base / "sample_splunk_dashboard.dsl").read_text(encoding="utf-8")
        self.values = json.loads((base / "sample_dashboard_values.json").read_text(encoding="utf-8"))
        self.engine = RootCauseEngine(correlation_window_minutes=90)

    def test_parses_thresholds_and_durations(self) -> None:
        policy = parse_dashboard_dsl(self.dsl_text)

        self.assertEqual(policy.variables["A"].metric, "ConsumedReadCapacityUnits")
        self.assertEqual(policy.variables["B"].metric, "AccountMaxTableLevelReads")
        self.assertEqual(len(policy.rules), 2)
        self.assertEqual(policy.rules[0].threshold_percent, 90.0)
        self.assertEqual(policy.rules[1].threshold_percent, 95.0)
        self.assertEqual(policy.rules[0].on_duration, "2m")
        self.assertEqual(policy.rules[0].off_duration, "5m")

    def test_evaluates_warn_and_alert(self) -> None:
        policy = parse_dashboard_dsl(self.dsl_text)
        generated_alerts = evaluate_dashboard_policy(policy, self.values, service="piam-preview-dynamodb")

        self.assertEqual(len(generated_alerts), 2)
        severities = sorted(item["severity"] for item in generated_alerts)
        self.assertEqual(severities, ["critical", "high"])
        self.assertTrue(all("ratio_percent" in item["metadata"] for item in generated_alerts))

    def test_dashboard_only_flow_identifies_capacity_issue(self) -> None:
        policy = parse_dashboard_dsl(self.dsl_text)
        generated_alerts = evaluate_dashboard_policy(policy, self.values, service="piam-preview-dynamodb")

        finding = self.engine.analyze(generated_alerts)

        self.assertIn("dynamodb", finding.probable_root_cause.lower())
        self.assertIn("capacity", finding.explanation.lower())
        self.assertTrue(any("capacity" in step.lower() or "autoscaling" in step.lower() for step in finding.remediation_steps))


if __name__ == "__main__":
    unittest.main()
