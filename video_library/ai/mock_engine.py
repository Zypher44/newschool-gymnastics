from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .feedback import build_mock_feedback
from .measurements import generate_mock_measurements


@dataclass
class AnalysisMomentResult:
    timestamp_seconds: Decimal
    moment_type: str
    label: str
    description: str
    severity: str
    confidence: Decimal
    measurements: dict[str, Any]
    display_order: int


@dataclass
class AnalysisEngineResult:
    detected_skill: str
    skill_confidence: Decimal
    summary: str
    strengths: list[str]
    improvements: list[str]
    measurements: dict[str, Any]
    raw_results: dict[str, Any]
    moments: list[AnalysisMomentResult]


class MockAnalysisEngine:
    """
    Demonstration engine used until real pose and vision
    processing are connected.
    """

    version = '0.2.0'
    source = 'mock'

    def analyze(
        self,
        analysis,
    ) -> AnalysisEngineResult:
        video = analysis.video

        detected_skill = (
            video.skill_name.strip()
            or analysis.requested_skill.strip()
            or 'Gymnastics skill'
        )

        measurements = generate_mock_measurements()

        feedback = build_mock_feedback(
            measurements=measurements,
        )

        moments = [
            AnalysisMomentResult(
                timestamp_seconds=Decimal('0.000'),
                moment_type='start',
                label='Start',
                description=(
                    'Beginning of the selected movement.'
                ),
                severity='info',
                confidence=Decimal('0.9500'),
                measurements={},
                display_order=1,
            ),
            AnalysisMomentResult(
                timestamp_seconds=Decimal('0.850'),
                moment_type='observation',
                label='Key body position',
                description=(
                    'Demonstration marker for a position '
                    'that a coach may want to review.'
                ),
                severity='positive',
                confidence=Decimal('0.8800'),
                measurements={
                    'shoulder_angle_degrees': 171.4,
                    'hip_angle_degrees': 166.8,
                },
                display_order=2,
            ),
            AnalysisMomentResult(
                timestamp_seconds=Decimal('1.650'),
                moment_type='observation',
                label='Alignment review',
                description=(
                    'Demonstration marker showing where '
                    'alignment feedback may appear.'
                ),
                severity='warning',
                confidence=Decimal('0.8200'),
                measurements={
                    'knee_angle_degrees': 174.2,
                },
                display_order=3,
            ),
            AnalysisMomentResult(
                timestamp_seconds=Decimal('2.850'),
                moment_type='finish',
                label='Finish',
                description=(
                    'End of the selected movement.'
                ),
                severity='info',
                confidence=Decimal('0.9300'),
                measurements={},
                display_order=4,
            ),
        ]

        return AnalysisEngineResult(
            detected_skill=detected_skill,
            skill_confidence=Decimal('0.9100'),
            summary=feedback['summary'],
            strengths=feedback['strengths'],
            improvements=feedback['improvements'],
            measurements=feedback['measurements'],
            raw_results={
                'mock_analysis': True,
                'warning': (
                    'These values are demonstration data '
                    'and were not measured from the video.'
                ),
                'pipeline_version': self.version,
                'engine': self.__class__.__name__,
            },
            moments=moments,
        )