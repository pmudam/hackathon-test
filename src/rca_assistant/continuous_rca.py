from __future__ import annotations

import json
import os
import subprocess
import time

from . import email_notifier
from .webex_utils import send_webex_message

DEFAULT_POLL_INTERVAL = 60


def resolve_poll_interval(value: str | None = None) -> int:
    raw_value = value if value is not None else os.getenv("RCA_POLL_INTERVAL", "")
    normalized = raw_value.strip() if isinstance(raw_value, str) else ""

    if not normalized:
        return DEFAULT_POLL_INTERVAL

    try:
        parsed = int(normalized)
    except (TypeError, ValueError):
        return DEFAULT_POLL_INTERVAL

    if parsed <= 0:
        return DEFAULT_POLL_INTERVAL

    return parsed


POLL_INTERVAL = resolve_poll_interval()


def idle_logging_enabled(value: str | None = None) -> bool:
    raw_value = value if value is not None else os.getenv("RCA_VERBOSE_IDLE", "")
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def parse_finding(rca_output: str) -> dict | None:
    try:
        parsed = json.loads(rca_output)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def is_no_alert_result(rca_output: str, stderr_output: str = "") -> bool:
    stderr_normalized = stderr_output.lower()
    if "no live incidents found" in stderr_normalized:
        return True

    finding = parse_finding(rca_output)
    if not finding:
        return False

    probable_root_cause = str(finding.get("probable_root_cause", "")).lower()
    explanation = str(finding.get("explanation", "")).lower()

    return "insufficient data" in probable_root_cause or "no live incidents found" in explanation


def format_notification(rca_output: str) -> str:
    finding = parse_finding(rca_output)
    if not finding:
        return f"**Splunk RCA Update**\n\n```\n{rca_output.strip()}\n```"

    evidence = "\n".join(f"- {item}" for item in finding.get("evidence", [])) or "- No evidence captured"
    remediation = "\n".join(f"- {item}" for item in finding.get("remediation_steps", [])) or "- No remediation steps available"

    return (
        "**Splunk RCA Update**\n\n"
        f"**Service:** {finding.get('affected_service', 'unknown')}\n"
        f"**Probable Cause:** {finding.get('probable_root_cause', 'unknown')}\n"
        f"**Confidence:** {finding.get('confidence', 'unknown')}\n\n"
        f"**Explanation:**\n{finding.get('explanation', 'No explanation available')}\n\n"
        f"**Evidence:**\n{evidence}\n\n"
        f"**Suggested Actions:**\n{remediation}"
    )


def run_rca_once() -> None:
    env = os.environ.copy()
    command = [
        "python3",
        "-m",
        "rca_assistant.cli",
        "--fetch-live",
        "--skip-dashboard-input",
        "--json",
    ]
    result = subprocess.run(command, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        print(f"[continuous_rca] RCA command failed with exit code {result.returncode}")
        return

    if is_no_alert_result(result.stdout, result.stderr):
        if idle_logging_enabled():
            if result.stderr:
                print(result.stderr)
            print("[continuous_rca] No alerts found for the detector in this polling cycle.")
        return

    print("\n[continuous_rca] Incident detected. Running RCA analysis...")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    print("[continuous_rca] Alert detected — sending notifications...")

    try:
        send_webex_message(format_notification(result.stdout))
        print("[continuous_rca] RCA result sent to Webex")
    except ValueError as error:
        print(f"[continuous_rca] Webex not configured: {error}")
    except Exception as error:
        print(f"[continuous_rca] Failed to send Webex notification: {error}")

    try:
        email_notifier.send_email_notification(result.stdout)
        print("[continuous_rca] RCA result sent via email")
    except ValueError as error:
        print(f"[continuous_rca] Email not configured: {error}")
    except Exception as error:
        print(f"[continuous_rca] Failed to send email notification: {error}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Continuous RCA monitoring")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single RCA poll and exit (used by GitHub Actions monitor mode)",
    )
    args = parser.parse_args()

    if args.once:
        print("[continuous_rca] Running single-shot RCA poll...")
        run_rca_once()
        print("[continuous_rca] Single-shot poll complete.")
        return

    print("[continuous_rca] Starting continuous RCA monitoring loop...")
    while True:
        run_rca_once()
        if idle_logging_enabled():
            print(f"[continuous_rca] Sleeping for {POLL_INTERVAL} seconds...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
