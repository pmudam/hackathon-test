from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SplunkObservabilityClient:
    def __init__(self, api_url: str, auth_token: str, timeout_seconds: int = 20) -> None:
        if not api_url.strip():
            raise ValueError("Splunk API URL is required")
        if not auth_token.strip():
            raise ValueError("Splunk auth token is required")

        self.api_url = api_url.rstrip("/")
        self.auth_token = auth_token.strip()
        self.timeout_seconds = timeout_seconds

    def fetch_detector_incidents(
        self,
        detector_id: str,
        endpoint_template: str = "/v2/detector/{detector_id}/incidents",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not detector_id.strip():
            raise ValueError("Detector id is required for live Splunk fetch")

        endpoint = endpoint_template.format(detector_id=detector_id.strip())
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{self.api_url}{endpoint}"
        if "?" in url:
            url = f"{url}&{urlencode({'limit': limit})}"
        else:
            url = f"{url}?{urlencode({'limit': limit})}"

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-SF-TOKEN": self.auth_token,
                "Authorization": f"Bearer {self.auth_token}",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Splunk API request failed ({exc.code}): {payload[:300]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Unable to reach Splunk API: {exc}") from exc

        data = json.loads(body)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if isinstance(data.get("results"), list):
                return data["results"]
            if isinstance(data.get("incidents"), list):
                return data["incidents"]
            if isinstance(data.get("data"), list):
                return data["data"]
        raise ValueError("Unexpected incident payload shape from Splunk API")


def incidents_to_alerts(
    incidents: list[dict[str, Any]],
    service_fallback: str = "splunk-service",
    detector_name_fallback: str = "splunk-detector",
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    for item in incidents:
        incident_id = str(item.get("id") or item.get("incidentId") or item.get("key") or "incident-unknown")
        severity = _normalize_severity(str(item.get("severity", "info")))
        timestamp = _normalize_timestamp(
            item.get("timestamp")
            or item.get("lastTriggeredTime")
            or item.get("eventTimestamp")
            or item.get("triggerTime")
        )

        dimensions = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
        service = (
            str(item.get("service") or "").strip()
            or str(dimensions.get("service") or dimensions.get("service_name") or dimensions.get("TableName") or "").strip()
            or service_fallback
        )

        detector_name = str(item.get("detectorName") or item.get("detector") or detector_name_fallback)
        title = str(item.get("title") or item.get("description") or detector_name)
        message = str(item.get("message") or item.get("summary") or item.get("description") or detector_name)
        category = "capacity" if "capacity" in f"{title} {message}".lower() else "api"

        alerts.append(
            {
                "id": incident_id,
                "timestamp": timestamp,
                "service": service,
                "severity": severity,
                "category": category,
                "title": title,
                "message": message,
                "metadata": {
                    "detector_name": detector_name,
                    "incident_status": item.get("status", "unknown"),
                    "raw_severity": item.get("severity"),
                    "source": "splunk-live",
                },
            }
        )

    return alerts


def _normalize_severity(value: str) -> str:
    normalized = value.lower().strip()
    if normalized in {"critical", "high", "major"}:
        return "critical"
    if normalized in {"warning", "warn", "medium"}:
        return "high"
    if normalized in {"minor", "info", "informational", "ok"}:
        return "info"
    return "high"


def _normalize_timestamp(raw: Any) -> str:
    if raw is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    if isinstance(raw, (int, float)):
        value = float(raw)
        if value > 10_000_000_000:
            value = value / 1000.0
        return datetime.fromtimestamp(value, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    text = str(raw).strip()
    if not text:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    if text.endswith("Z"):
        return text

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
