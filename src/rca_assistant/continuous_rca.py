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


def format_notification(rca_output: str) -> str:
    try:
        finding = json.loads(rca_output)
    except json.JSONDecodeError:
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
    print("\n[continuous_rca] Running RCA analysis...")
    result = subprocess.run(command, env=env, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print(f"[continuous_rca] RCA command failed with exit code {result.returncode}")
        return

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
    print("[continuous_rca] Starting continuous RCA monitoring loop...")
    while True:
        run_rca_once()
        print(f"[continuous_rca] Sleeping for {POLL_INTERVAL} seconds...")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
