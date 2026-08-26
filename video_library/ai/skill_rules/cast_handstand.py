from .base import (
    BaseSkillRuleSet,
    SkillObservation,
)


class CastHandstandRuleSet(
    BaseSkillRuleSet
):
    skill_name = 'Cast Handstand'
    rule_version = 'cast_handstand_v1'

    def evaluate_frame(
        self,
        *,
        phase,
        measurements,
    ):
        observations = []

        quality = self.get_analysis_quality(
            measurements
        )

        if not quality[
            'usable'
        ]:
            return observations

        gymnastics = (
            measurements.get(
                'gymnastics_measurements'
            )
            or {}
        )

        knee_data = (
            gymnastics.get(
                'knee_extension'
            )
            or {}
        )

        hip_data = (
            gymnastics.get(
                'hip_position'
            )
            or {}
        )

        shoulder_data = (
            gymnastics.get(
                'shoulder_position'
            )
            or {}
        )

        knee_angle = (
            knee_data.get(
                'average_angle'
            )
        )

        hip_angle = (
            hip_data.get(
                'average_angle'
            )
        )

        shoulder_angle = (
            shoulder_data.get(
                'average_angle'
            )
        )

        observation_confidence = (
            self.calculate_observation_confidence(
                pose_visibility=quality[
                    'pose_visibility'
                ],
                phase_confidence=quality[
                    'phase_confidence'
                ],
            )
        )


        if phase == 'entry':

            if (
                knee_angle is not None
                and knee_angle < 160
            ):
                observations.append(
                    SkillObservation(
                        code=(
                            'cast_entry_knee_bend'
                        ),
                        title=(
                            'Knee Bend During Entry'
                        ),
                        description=(
                            'The measured knee angle is '
                            'below the current entry threshold.'
                        ),
                        severity='warning',
                        phase=phase,
                        measurements={
                            'knee_angle': (
                                knee_angle
                            ),
                        },
                        evidence={
                            'knee_angle': (
                                knee_angle
                            ),
                            'threshold_degrees': (
                                160
                            ),
                            'pose_visibility': (
                                quality[
                                    'pose_visibility'
                                ]
                            ),
                            'phase_confidence': (
                                quality[
                                    'phase_confidence'
                                ]
                            ),
                        },
                        confidence=(
                            observation_confidence
                        ),
                        rule_version=(
                            self.rule_version
                        ),
                    )
                )


        if phase in [
            'main_action',
            'peak',
        ]:

            if (
                hip_angle is not None
                and hip_angle < 160
            ):
                observations.append(
                    SkillObservation(
                        code='cast_hip_closure',
                        title='Hip Closure',
                        description=(
                            'The measured hip angle shows '
                            'a closed body position during '
                            'the current cast phase.'
                        ),
                        severity='warning',
                        phase=phase,
                        measurements={
                            'hip_angle': hip_angle,
                        },
                        evidence={
                            'hip_angle': hip_angle,
                            'threshold_degrees': 160,
                            'pose_visibility': (
                                quality[
                                    'pose_visibility'
                                ]
                            ),
                            'phase_confidence': (
                                quality[
                                    'phase_confidence'
                                ]
                            ),
                        },
                        confidence=(
                            observation_confidence
                        ),
                        rule_version=(
                            self.rule_version
                        ),
                    )
                )


            if (
                shoulder_angle is not None
                and shoulder_angle < 155
            ):
                observations.append(
                    SkillObservation(
                        code='cast_shoulder_angle',
                        title='Shoulder Angle',
                        description=(
                            'The measured shoulder angle '
                            'is below the current analysis '
                            'threshold.'
                        ),
                        severity='warning',
                        phase=phase,
                        measurements={
                            'shoulder_angle': (
                                shoulder_angle
                            ),
                        },
                        evidence={
                            'shoulder_angle': (
                                shoulder_angle
                            ),
                            'threshold_degrees': (
                                155
                            ),
                            'pose_visibility': (
                                quality[
                                    'pose_visibility'
                                ]
                            ),
                            'phase_confidence': (
                                quality[
                                    'phase_confidence'
                                ]
                            ),
                        },
                        confidence=(
                            observation_confidence
                        ),
                        rule_version=(
                            self.rule_version
                        ),
                    )
                )


            if (
                knee_angle is not None
                and knee_angle >= 170
            ):
                observations.append(
                    SkillObservation(
                        code='cast_straight_legs',
                        title=(
                            'Straight Leg Position'
                        ),
                        description=(
                            'The measured knee angle '
                            'indicates a nearly straight '
                            'leg position.'
                        ),
                        severity='positive',
                        phase=phase,
                        measurements={
                            'knee_angle': (
                                knee_angle
                            ),
                        },
                        evidence={
                            'knee_angle': (
                                knee_angle
                            ),
                            'threshold_degrees': (
                                170
                            ),
                            'pose_visibility': (
                                quality[
                                    'pose_visibility'
                                ]
                            ),
                            'phase_confidence': (
                                quality[
                                    'phase_confidence'
                                ]
                            ),
                        },
                        confidence=(
                            observation_confidence
                        ),
                        rule_version=(
                            self.rule_version
                        ),
                    )
                )


        if phase == 'peak':

            if (
                hip_angle is not None
                and hip_angle >= 170
                and shoulder_angle is not None
                and shoulder_angle >= 165
            ):
                observations.append(
                    SkillObservation(
                        code=(
                            'cast_peak_alignment'
                        ),
                        title=(
                            'Peak Body Alignment'
                        ),
                        description=(
                            'Hip and shoulder measurements '
                            'show a relatively open body '
                            'line at the detected peak phase.'
                        ),
                        severity='positive',
                        phase=phase,
                        measurements={
                            'hip_angle': (
                                hip_angle
                            ),
                            'shoulder_angle': (
                                shoulder_angle
                            ),
                        },
                        evidence={
                            'hip_angle': (
                                hip_angle
                            ),
                            'hip_threshold': (
                                170
                            ),
                            'shoulder_angle': (
                                shoulder_angle
                            ),
                            'shoulder_threshold': (
                                165
                            ),
                            'pose_visibility': (
                                quality[
                                    'pose_visibility'
                                ]
                            ),
                            'phase_confidence': (
                                quality[
                                    'phase_confidence'
                                ]
                            ),
                        },
                        confidence=(
                            observation_confidence
                        ),
                        rule_version=(
                            self.rule_version
                        ),
                    )
                )

        return observations