from dataclasses import dataclass
from typing import Any


@dataclass
class SkillObservation:
    code: str
    title: str
    description: str
    severity: str
    phase: str
    measurements: dict[str, Any]

    evidence: dict[str, Any]
    confidence: float
    rule_version: str


class BaseSkillRuleSet:
    skill_name = ''
    rule_version = '1.0'

    minimum_pose_visibility = 0.60
    minimum_phase_confidence = 0.55

    def matches(
        self,
        skill_name: str,
    ) -> bool:
        return (
            skill_name.strip().lower()
            == self.skill_name.lower()
        )

    def get_analysis_quality(
        self,
        measurements: dict[str, Any],
    ) -> dict[str, Any]:
        gymnastics = (
            measurements.get(
                'gymnastics_measurements'
            )
            or {}
        )

        pose_visibility = (
            gymnastics.get(
                'average_landmark_visibility'
            )
        )

        phase_confidence = (
            measurements.get(
                'skill_phase_confidence'
            )
        )

        pose_visibility = (
            float(pose_visibility)
            if pose_visibility is not None
            else 0.0
        )

        phase_confidence = (
            float(phase_confidence)
            if phase_confidence is not None
            else 0.0
        )

        usable = (
            pose_visibility
            >= self.minimum_pose_visibility
            and
            phase_confidence
            >= self.minimum_phase_confidence
        )

        return {
            'usable': usable,
            'pose_visibility': (
                round(
                    pose_visibility,
                    3,
                )
            ),
            'phase_confidence': (
                round(
                    phase_confidence,
                    3,
                )
            ),
        }

    def calculate_observation_confidence(
        self,
        *,
        pose_visibility,
        phase_confidence,
    ):
        confidence = (
            pose_visibility
            * 0.60
            +
            phase_confidence
            * 0.40
        )

        return round(
            max(
                0.0,
                min(
                    1.0,
                    confidence,
                ),
            ),
            3,
        )

    def evaluate_frame(
        self,
        *,
        phase: str,
        measurements: dict[str, Any],
    ) -> list[SkillObservation]:
        raise NotImplementedError