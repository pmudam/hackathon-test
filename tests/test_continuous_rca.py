import json
import unittest

from rca_assistant.continuous_rca import format_notification, idle_logging_enabled, is_no_alert_result, resolve_poll_interval


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

    def test_resolve_poll_interval_defaults_on_empty(self):
        self.assertEqual(resolve_poll_interval(""), 60)
        self.assertEqual(resolve_poll_interval("   "), 60)

    def test_resolve_poll_interval_defaults_on_invalid(self):
        self.assertEqual(resolve_poll_interval("abc"), 60)
        self.assertEqual(resolve_poll_interval("0"), 60)
        self.assertEqual(resolve_poll_interval("-10"), 60)

    def test_resolve_poll_interval_accepts_positive_integer(self):
        self.assertEqual(resolve_poll_interval("15"), 15)

    def test_idle_logging_enabled_false_by_default(self):
        self.assertFalse(idle_logging_enabled(""))
        self.assertFalse(idle_logging_enabled("false"))

    def test_idle_logging_enabled_true_values(self):
        self.assertTrue(idle_logging_enabled("true"))
        self.assertTrue(idle_logging_enabled("1"))

    def test_is_no_alert_result_detects_stderr_message(self):
        self.assertTrue(is_no_alert_result("{}", "No live incidents found for the selected detector."))

    def test_is_no_alert_result_detects_insufficient_data_finding(self):
        payload = json.dumps(
            {
                "affected_service": "orders-api",
                "probable_root_cause": "Insufficient data",
                "confidence": 0.0,
                "explanation": "No live incidents found for the selected detector.",
                "evidence": [],
                "remediation_steps": [],
            }
        )

        self.assertTrue(is_no_alert_result(payload))

    def test_is_no_alert_result_false_for_real_alert(self):
        payload = json.dumps(
            {
                "affected_service": "orders-api",
                "probable_root_cause": "High latency in dependency",
                "confidence": 0.92,
                "explanation": "Dependency saturation caused the alert cascade.",
                "evidence": ["p95 latency exceeded threshold"],
                "remediation_steps": ["Scale the dependency"],
            }
        )

        self.assertFalse(is_no_alert_result(payload))


if __name__ == "__main__":
    unittest.main()
