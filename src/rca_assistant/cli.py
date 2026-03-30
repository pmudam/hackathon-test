from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .dashboard_adapter import evaluate_dashboard_policy
from .dashboard_parser import parse_dashboard_dsl
from .engine import RootCauseEngine
from .splunk_client import SplunkObservabilityClient, incidents_to_alerts


def _load_alert_file(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Alert file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected list of alerts in {path}")
    return payload


def _load_optional_alert_file(path_value: str | None) -> list[dict]:
    if not path_value:
        return []
    return _load_alert_file(Path(path_value))


def _load_json_object(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _load_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Root Cause Assistant for Splunk dashboard monitoring")
    parser.add_argument("--splunk-alerts", help="Optional Splunk alerts JSON")
    parser.add_argument("--fetch-live", action="store_true", help="Fetch live incidents from Splunk Observability")
    parser.add_argument("--splunk-api-url", help="Splunk Observability API URL (or env SPLUNK_API_URL)")
    parser.add_argument("--splunk-auth-token", help="Splunk auth token (or env SPLUNK_AUTH_TOKEN)")
    parser.add_argument("--splunk-detector-id", help="Detector id to fetch incidents for (or env SPLUNK_DETECTOR_ID)")
    parser.add_argument(
        "--splunk-incidents-endpoint",
        default="/v2/detector/{detector_id}/incidents",
        help="Incidents endpoint template with {detector_id} placeholder",
    )
    parser.add_argument("--splunk-live-limit", type=int, default=50, help="Max number of live incidents to fetch")
    parser.add_argument("--splunk-timeout-seconds", type=int, default=20, help="Timeout for Splunk API requests")
    parser.add_argument("--skip-dashboard-input", action="store_true", help="Skip local dashboard DSL/value evaluation")
    parser.add_argument(
        "--dashboard-dsl",
        default="data/sample_splunk_dashboard.dsl",
        help="Splunk dashboard detection DSL text file",
    )
    parser.add_argument(
        "--dashboard-values",
        default="data/sample_dashboard_values.json",
        help="Dashboard values JSON object with A and B",
    )
    parser.add_argument("--dashboard-service", default="piam-preview-dynamodb", help="Service name for generated dashboard alerts")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    splunk_alerts = _load_optional_alert_file(args.splunk_alerts)

    if args.fetch_live:
        splunk_api_url = args.splunk_api_url or os.getenv("SPLUNK_API_URL", "")
        splunk_auth_token = args.splunk_auth_token or os.getenv("SPLUNK_AUTH_TOKEN", "") or os.getenv("SPLUNK_API_TOKEN", "")
        splunk_detector_id = args.splunk_detector_id or os.getenv("SPLUNK_DETECTOR_ID", "")

        if not splunk_api_url:
            raise ValueError("Provide --splunk-api-url or set SPLUNK_API_URL for live fetch")
        if not splunk_auth_token:
            raise ValueError("Provide --splunk-auth-token or set SPLUNK_AUTH_TOKEN for live fetch")
        if not splunk_detector_id:
            raise ValueError("Provide --splunk-detector-id or set SPLUNK_DETECTOR_ID for live fetch")

        client = SplunkObservabilityClient(
            api_url=splunk_api_url,
            auth_token=splunk_auth_token,
            timeout_seconds=args.splunk_timeout_seconds,
        )
        incidents = client.fetch_detector_incidents(
            detector_id=splunk_detector_id,
            endpoint_template=args.splunk_incidents_endpoint,
            limit=args.splunk_live_limit,
        )
        splunk_alerts.extend(
            incidents_to_alerts(
                incidents,
                service_fallback=args.dashboard_service,
                detector_name_fallback=splunk_detector_id,
            )
        )

    if not args.skip_dashboard_input and args.dashboard_dsl and args.dashboard_values:
        dsl_text = _load_text_file(Path(args.dashboard_dsl))
        dashboard_values = _load_json_object(Path(args.dashboard_values))
        policy = parse_dashboard_dsl(dsl_text)
        dashboard_alerts = evaluate_dashboard_policy(policy, dashboard_values, service=args.dashboard_service)
        splunk_alerts.extend(dashboard_alerts)

    if not splunk_alerts:
        if args.fetch_live and args.skip_dashboard_input:
            print(
                "No live incidents found for the selected detector. Returning an insufficient-data RCA response.",
                file=sys.stderr,
            )
        else:
            raise ValueError("Provide Splunk dashboard inputs or --splunk-alerts to analyze incidents")

    engine = RootCauseEngine(correlation_window_minutes=90)
    finding = engine.analyze(splunk_alerts)

    if args.json:
        print(json.dumps(asdict(finding), indent=2))
        return

    print("\n=== AI Root Cause Assistant ===")
    print(f"Affected service : {finding.affected_service}")
    print(f"Probable cause   : {finding.probable_root_cause}")
    print(f"Confidence       : {finding.confidence}")
    print(f"\nExplanation:\n- {finding.explanation}")
    print("\nEvidence:")
    for item in finding.evidence:
        print(f"- {item}")
    print("\nSuggested actions:")
    for step in finding.remediation_steps:
        print(f"- {step}")


if __name__ == "__main__":
    main()
