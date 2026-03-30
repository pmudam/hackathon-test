from __future__ import annotations

import re

from .dashboard_models import DashboardPolicy, DetectionRule, SignalVariable

VAR_PATTERN = re.compile(r"^([A-Z])\s*=\s*data\('([^']+)'", re.MULTILINE)
RULE_PATTERN = re.compile(
    r"detect\(when\(A/B \* 100 > threshold\((\d+(?:\.\d+)?)\), '([0-9]+m)'\),\s*"
    r"off=when\(A/B \* 100 <= threshold\((\d+(?:\.\d+)?)\), '([0-9]+m)'\)\)"
    r"\.publish\('([^']+)'\)",
    re.MULTILINE,
)


def parse_dashboard_dsl(dsl_text: str) -> DashboardPolicy:
    if not dsl_text.strip():
        raise ValueError("Dashboard DSL content is empty")

    variables: dict[str, SignalVariable] = {}
    for match in VAR_PATTERN.finditer(dsl_text):
        name, metric = match.groups()
        variables[name] = SignalVariable(name=name, metric=metric)

    if "A" not in variables or "B" not in variables:
        raise ValueError("Expected variables A and B in dashboard DSL")

    rules: list[DetectionRule] = []
    for match in RULE_PATTERN.finditer(dsl_text):
        threshold_high, on_duration, threshold_low, off_duration, publish_name = match.groups()
        if threshold_high != threshold_low:
            raise ValueError("Mismatched threshold in detect/off clauses")

        publish_prefix = publish_name.split(":", 1)[0].strip().upper()
        level = "warn" if publish_prefix == "WARN" else "alert"

        rules.append(
            DetectionRule(
                level=level,
                threshold_percent=float(threshold_high),
                on_duration=on_duration,
                off_duration=off_duration,
                publish_name=publish_name,
            )
        )

    if not rules:
        raise ValueError("No detection rules found in dashboard DSL")

    return DashboardPolicy(variables=variables, ratio_expression="A/B*100", rules=rules)
