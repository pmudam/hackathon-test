import json
import unittest

from rca_assistant.continuous_rca import format_notification


class ContinuousRcaTests(unittest.TestCase):
    def test_format_notification_from_json(self):
        payload = json.dumps(
            {
                "affected_service": "orders-api",
                "probable_root_cause": "High latency in dependency",
                "confidence": 0.92,
                "explanation": "Dependency saturation caused the alert cascade.",
                "evidence": ["p95 latency exceeded threshold", "error rate increased"],
                "remediation_steps": ["Scale the dependency", "Drain unhealthy instances"],
            }
        )

        message = format_notification(payload)

        self.assertIn("**Service:** orders-api", message)
        self.assertIn("**Probable Cause:** High latency in dependency", message)
        self.assertIn("- p95 latency exceeded threshold", message)
        self.assertIn("- Scale the dependency", message)

    def test_format_notification_from_plain_text(self):
        message = format_notification("raw output")

        self.assertIn("**Splunk RCA Update**", message)
        self.assertIn("raw output", message)


if __name__ == "__main__":
    unittest.main()
