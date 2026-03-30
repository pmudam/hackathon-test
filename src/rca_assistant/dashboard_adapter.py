from __future__ import annotations

from datetime import datetime, timezone

from .dashboard_models import DashboardPolicy


def evaluate_dashboard_policy(
    policy: DashboardPolicy,
    values: dict,
    service: str = "dynamodb",
    source: str = "splunk-dashboard",
) -> list[dict]:
    if "A" not in values or "B" not in values:
        raise ValueError("Dashboard values must include numeric A and B")

    a_value = float(values["A"])
    b_value = float(values["B"])
    if b_value <= 0:
        raise ValueError("Dashboard value B must be greater than zero")

    ratio_percent = (a_value / b_value) * 100.0
    timestamp = values.get("timestamp")
    if not timestamp:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    table_name = values.get("TableName", "staging-prometheus")
    alerts: list[dict] = []

    for rule in policy.rules:
        if ratio_percent > rule.threshold_percent:
            severity = "high" if rule.level == "warn" else "critical"
            category = "capacity"
            alerts.append(
                {
                    "id": f"dashboard-{rule.level}-{int(rule.threshold_percent)}",
                    "timestamp": timestamp,
                    "service": service,
                    "severity": severity,
                    "category": category,
                    "title": rule.publish_name,
                    "message": (
                        f"DynamoDB read capacity utilization at {ratio_percent:.2f}% exceeds "
                        f"threshold {rule.threshold_percent:.0f}% for {rule.on_duration}"
                    ),
                    "metadata": {
                        "ratio_percent": round(ratio_percent, 2),
                        "threshold_percent": rule.threshold_percent,
                        "on_duration": rule.on_duration,
                        "off_duration": rule.off_duration,
                        "table_name": table_name,
                        "metric_A": policy.variables["A"].metric,
                        "metric_B": policy.variables["B"].metric,
                        "source": source,
                        "dashboard_platform": "splunk",
                    },
                }
            )

    return alerts
