from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Alert:
    source: str
    alert_id: str
    timestamp: datetime
    service: str
    severity: str
    category: str
    title: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], source: str) -> "Alert":
        raw_timestamp = str(payload.get("timestamp", "")).strip()
        if raw_timestamp.endswith("Z"):
            raw_timestamp = raw_timestamp.replace("Z", "+00:00")

        return cls(
            source=source,
            alert_id=str(payload.get("id", payload.get("alert_id", "unknown"))),
            timestamp=datetime.fromisoformat(raw_timestamp),
            service=str(payload.get("service", "unknown-service")),
            severity=str(payload.get("severity", "info")).lower(),
            category=str(payload.get("category", "general")).lower(),
            title=str(payload.get("title", "")),
            message=str(payload.get("message", "")),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass
class RootCauseFinding:
    probable_root_cause: str
    confidence: float
    affected_service: str
    explanation: str
    evidence: list[str]
    remediation_steps: list[str]
