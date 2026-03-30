from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalVariable:
    name: str
    metric: str


@dataclass
class DetectionRule:
    level: str
    threshold_percent: float
    on_duration: str
    off_duration: str
    publish_name: str


@dataclass
class DashboardPolicy:
    variables: dict[str, SignalVariable]
    ratio_expression: str
    rules: list[DetectionRule]
