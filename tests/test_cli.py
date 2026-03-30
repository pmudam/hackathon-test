import unittest

from rca_assistant.cli import debug_incident_logging_enabled


class CliTests(unittest.TestCase):
    def test_debug_incident_logging_enabled_true_values(self):
        for value in ("1", "true", "TRUE", "yes", "on"):
            with self.subTest(value=value):
                self.assertTrue(debug_incident_logging_enabled(value))

    def test_debug_incident_logging_enabled_false_values(self):
        for value in (None, "", "0", "false", "no", "off"):
            with self.subTest(value=value):
                self.assertFalse(debug_incident_logging_enabled(value))


if __name__ == "__main__":
    unittest.main()
