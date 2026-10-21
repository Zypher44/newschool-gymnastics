from dataclasses import dataclass
from typing import Any

@dataclass
class AnalysisEngineResult:
    detected_skill: str
    skill_confidence: float | None
    summary: str
    strengths: list[str]
    improvements: list[str]
    measurements: dict[str, Any]
    raw_results: dict[str, Any]
    moments: list
