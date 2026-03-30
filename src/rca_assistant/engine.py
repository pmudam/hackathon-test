from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Iterable

from .models import Alert, RootCauseFinding


class RootCauseEngine:
    def __init__(self, correlation_window_minutes: int = 60) -> None:
        self.correlation_window = timedelta(minutes=correlation_window_minutes)

    def analyze(self, splunk_alerts: list[dict]) -> RootCauseFinding:
        alerts = self._normalize(splunk_alerts)
        if not alerts:
            return RootCauseFinding(
                probable_root_cause="Insufficient data",
                confidence=0.0,
                affected_service="unknown-service",
                explanation="No alerts were provided for analysis.",
                evidence=[],
                remediation_steps=["Ensure Splunk detector and dashboard alert feeds are connected."],
            )

        affected_service = Counter(alert.service for alert in alerts).most_common(1)[0][0]
        alerts = sorted(alerts, key=lambda item: item.timestamp)

        score = {"deployment": 0.0, "memory": 0.0, "cpu": 0.0, "api_failure": 0.0, "capacity": 0.0}
        events: dict[str, list[Alert]] = {
            "deployment": [],
            "memory": [],
            "cpu": [],
            "api_failure": [],
            "capacity": [],
        }

        for alert in alerts:
            categories = self._classify(alert)
            for category in categories:
                score[category] += 1.0
                events[category].append(alert)

        temporal_chain = self._has_temporal_chain(events)

        if all(events[k] for k in ["deployment", "memory", "cpu", "api_failure"]) and temporal_chain:
            root_cause = "Recent deployment introduced a memory leak that triggered CPU spike and API failures"
            confidence = min(0.95, 0.55 + 0.1 * sum(bool(events[k]) for k in events) + 0.1)
            explanation = (
                "A deployment event is followed by memory leak signals, then CPU saturation, and finally "
                "API failures in the same correlation window. This pattern strongly indicates a bad release "
                "causing resource exhaustion."
            )
            remediation_steps = [
                "Rollback the most recent deployment to the last known good version.",
                "Temporarily scale out instances to reduce customer impact.",
                "Capture heap/profile data and patch the memory leak before redeploying.",
                "Add canary checks for memory growth and 5xx error budget burn.",
            ]
        else:
            dominant = max(score, key=score.get)
            root_cause, explanation, remediation_steps = self._fallback_recommendation(dominant)
            confidence = min(0.8, 0.35 + 0.12 * score[dominant] + (0.08 if temporal_chain else 0.0))

        evidence = self._build_evidence(events)

        return RootCauseFinding(
            probable_root_cause=root_cause,
            confidence=round(confidence, 2),
            affected_service=affected_service,
            explanation=explanation,
            evidence=evidence,
            remediation_steps=remediation_steps,
        )

    def _normalize(self, splunk_alerts: list[dict]) -> list[Alert]:
        normalized: list[Alert] = []
        normalized.extend(Alert.from_dict(item, source="splunk") for item in splunk_alerts)
        return normalized

    def _classify(self, alert: Alert) -> set[str]:
        text = f"{alert.category} {alert.title} {alert.message}".lower()
        categories: set[str] = set()

        if any(token in text for token in ["deploy", "release", "rollout", "rollback"]):
            categories.add("deployment")

        if any(token in text for token in ["memory leak", "out of memory", "oom", "heap", "rss"]):
            categories.add("memory")

        if any(token in text for token in ["cpu", "throttle", "saturation"]):
            categories.add("cpu")

        if any(
            token in text
            for token in [
                "dynamodb",
                "read capacity",
                "consumedreadcapacityunits",
                "accountmaxtablelevelreads",
                "capacity utilization",
                "hot partition",
            ]
        ):
            categories.add("capacity")

        if any(token in text for token in ["api failure", "5xx", "timeout", "error rate", "latency"]):
            categories.add("api_failure")

        metric_name = str(alert.metadata.get("metric_name", "")).lower()
        metric_value = self._metric_value(alert.metadata)
        if metric_name == "memoryutilization" and metric_value >= 80:
            categories.add("memory")
        if metric_name == "cpuutilization" and metric_value >= 85:
            categories.add("cpu")
        if metric_name in {"consumedreadcapacityunits", "accountmaxtablelevelreads"}:
            categories.add("capacity")

        if self._metric_value(alert.metadata, "ratio_percent") >= 90:
            categories.add("capacity")

        if not categories:
            categories.add("api_failure" if alert.severity in {"critical", "high"} else "cpu")
        return categories

    def _metric_value(self, metadata: dict, preferred_key: str | None = None) -> float:
        keys = [preferred_key] if preferred_key else []
        keys.extend(["metric_value", "value", "current", "observed"])
        for key in keys:
            if not key:
                continue
            if key in metadata:
                try:
                    return float(metadata[key])
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def _has_temporal_chain(self, events: dict[str, list[Alert]]) -> bool:
        if not all(events[k] for k in ["deployment", "memory", "cpu", "api_failure"]):
            return False

        deployment_time = min(item.timestamp for item in events["deployment"])
        memory_time = min(item.timestamp for item in events["memory"])
        cpu_time = min(item.timestamp for item in events["cpu"])
        api_time = min(item.timestamp for item in events["api_failure"])

        ordered = deployment_time <= memory_time <= cpu_time <= api_time
        within_window = (api_time - deployment_time) <= self.correlation_window
        return ordered and within_window

    def _build_evidence(self, events: dict[str, list[Alert]]) -> list[str]:
        evidence: list[str] = []
        for category, category_events in events.items():
            for event in category_events[:2]:
                evidence.append(
                    f"[{event.timestamp.isoformat()}] {event.source}:{category} - {event.title or event.message}"
                )
        return evidence

    def _fallback_recommendation(self, dominant: str) -> tuple[str, str, list[str]]:
        if dominant == "memory":
            return (
                "Memory pressure likely causing instability",
                "Alerts indicate memory growth and potential leaks affecting service health.",
                [
                    "Restart unhealthy instances and enable memory profiling.",
                    "Inspect recent code paths with allocations and cache growth.",
                    "Scale memory limits temporarily while patch is developed.",
                ],
            )
        if dominant == "cpu":
            return (
                "CPU saturation is the primary symptom",
                "CPU-related alerts dominate and are likely driving latency and failures.",
                [
                    "Scale compute capacity or increase autoscaling aggressiveness.",
                    "Profile hot endpoints and expensive background jobs.",
                    "Throttle bursty traffic or heavy batch workloads.",
                ],
            )
        if dominant == "api_failure":
            return (
                "API error conditions are the main driver",
                "Application errors and failed API requests are the strongest shared signal.",
                [
                    "Check top failing endpoints and recent config changes.",
                    "Enable circuit breaking/retries for critical downstream dependencies.",
                    "Roll back recent changes if failure rate increased immediately after release.",
                ],
            )
        if dominant == "capacity":
            return (
                "DynamoDB read capacity is nearing or exceeding configured limits",
                "The Splunk dashboard shows sustained read-capacity utilization above the configured threshold, "
                "which can lead to throttling, latency, or failed requests.",
                [
                    "Increase DynamoDB read capacity or verify autoscaling targets.",
                    "Check for hot partitions or uneven key distribution causing concentrated read load.",
                    "Reduce burst traffic, cache read-heavy endpoints, or spread requests across partitions.",
                ],
            )
        return (
            "Recent deployment is the most likely trigger",
            "A release event appears correlated with subsequent production instability.",
            [
                "Compare current release against last stable build.",
                "Roll back or shift traffic away from the new version.",
                "Add staged rollout and anomaly detection before full rollout.",
            ],
        )
