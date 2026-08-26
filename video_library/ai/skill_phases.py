from dataclasses import dataclass
from typing import Any


@dataclass
class SkillPhaseResult:
    phase: str
    confidence: float
    reason: str


PHASE_SETUP = 'setup'
PHASE_ENTRY = 'entry'
PHASE_MAIN_ACTION = 'main_action'
PHASE_PEAK = 'peak'
PHASE_EXIT = 'exit'
PHASE_FINISH = 'finish'


def _average(
    values,
):
    valid_values = [
        float(value)
        for value in values
        if value is not None
    ]

    if not valid_values:
        return None

    return (
        sum(valid_values)
        / len(valid_values)
    )


def _normalize_skill_name(
    skill_name,
):
    normalized = (
        skill_name
        or ''
    ).strip().lower()

    normalized = ' '.join(
        normalized.split()
    )

    aliases = {
        'hand stand': 'handstand',

        'cast to handstand': (
            'cast handstand'
        ),

        'cast-handstand': (
            'cast handstand'
        ),

        'bhs': (
            'back handspring'
        ),

        'backhandspring': (
            'back handspring'
        ),

        'fhs': (
            'front handspring'
        ),

        'fronthandspring': (
            'front handspring'
        ),

        'round off': (
            'roundoff'
        ),

        'backward tuck': (
            'back tuck'
        ),

        'back salto tuck': (
            'back tuck'
        ),
    }

    return aliases.get(
        normalized,
        normalized,
    )


def classify_frame_phase(
    *,
    frame_index: int,
    total_frames: int,
    gymnastics_measurements: dict[str, Any],
    motion_metrics: dict[str, Any] | None = None,
    skill_name: str = '',
) -> SkillPhaseResult:
    """
    Classify one analyzed frame into a broad gymnastics
    movement phase.

    Inputs include:
    - position within the analyzed sequence
    - body measurements
    - frame-to-frame motion
    - skill name

    Skill-specific rules are evaluated before the generic
    fallback classifier.
    """

    motion_metrics = (
        motion_metrics
        or {}
    )

    normalized_skill = (
        _normalize_skill_name(
            skill_name
        )
    )

    if total_frames <= 0:

        return SkillPhaseResult(
            phase=PHASE_MAIN_ACTION,
            confidence=0.30,
            reason=(
                'Frame count was unavailable, so the '
                'movement phase could not be classified '
                'reliably.'
            ),
        )


    #
    # ---------------------------------------------------------
    # POSITION WITHIN ANALYZED SEQUENCE
    # ---------------------------------------------------------
    #

    denominator = max(
        total_frames - 1,
        1,
    )

    progress = (
        frame_index
        / denominator
    )


    #
    # ---------------------------------------------------------
    # GYMNASTICS MEASUREMENTS
    # ---------------------------------------------------------
    #

    hip_data = (
        gymnastics_measurements.get(
            'hip_position'
        )
        or {}
    )

    knee_data = (
        gymnastics_measurements.get(
            'knee_extension'
        )
        or {}
    )

    shoulder_data = (
        gymnastics_measurements.get(
            'shoulder_position'
        )
        or {}
    )


    hip_angle = (
        hip_data.get(
            'average_angle'
        )
    )

    knee_angle = (
        knee_data.get(
            'average_angle'
        )
    )

    shoulder_angle = (
        shoulder_data.get(
            'average_angle'
        )
    )


    #
    # ---------------------------------------------------------
    # TORSO ORIENTATION
    # ---------------------------------------------------------
    #

    left_torso = (
        gymnastics_measurements.get(
            'left_torso_orientation'
        )
    )

    right_torso = (
        gymnastics_measurements.get(
            'right_torso_orientation'
        )
    )

    torso_orientation = _average([
        left_torso,
        right_torso,
    ])


    #
    # ---------------------------------------------------------
    # LEG ORIENTATION
    # ---------------------------------------------------------
    #

    left_leg = (
        gymnastics_measurements.get(
            'left_leg_orientation'
        )
    )

    right_leg = (
        gymnastics_measurements.get(
            'right_leg_orientation'
        )
    )

    leg_orientation = _average([
        left_leg,
        right_leg,
    ])


    #
    # ---------------------------------------------------------
    # MOTION METRICS
    # ---------------------------------------------------------
    #

    movement_score = (
        motion_metrics.get(
            'movement_score'
        )
        or 0.0
    )

    hip_change = (
        motion_metrics.get(
            'hip_angle_change'
        )
    )

    knee_change = (
        motion_metrics.get(
            'knee_angle_change'
        )
    )

    shoulder_change = (
        motion_metrics.get(
            'shoulder_angle_change'
        )
    )

    torso_change = (
        motion_metrics.get(
            'torso_orientation_change'
        )
    )


    #
    # ---------------------------------------------------------
    # USEFUL BODY STATES
    # ---------------------------------------------------------
    #

    straight_knees = (
        knee_angle is not None
        and knee_angle >= 165
    )

    very_straight_knees = (
        knee_angle is not None
        and knee_angle >= 172
    )


    open_hips = (
        hip_angle is not None
        and hip_angle >= 160
    )

    very_open_hips = (
        hip_angle is not None
        and hip_angle >= 170
    )


    open_shoulders = (
        shoulder_angle is not None
        and shoulder_angle >= 155
    )

    very_open_shoulders = (
        shoulder_angle is not None
        and shoulder_angle >= 170
    )


    vertical_torso = (
        torso_orientation is not None
        and torso_orientation >= 65
    )

    very_vertical_torso = (
        torso_orientation is not None
        and torso_orientation >= 75
    )


    relatively_stable = (
        movement_score < 8
    )

    very_stable = (
        movement_score < 4
    )


    significant_movement = (
        movement_score >= 8
    )

    high_movement = (
        movement_score >= 15
    )


    #
    # =========================================================
    # SETUP
    # =========================================================
    #

    if progress <= 0.10:

        return SkillPhaseResult(
            phase=PHASE_SETUP,
            confidence=0.94,
            reason=(
                'Frame occurs at the beginning of the '
                'analyzed movement sequence.'
            ),
        )


    #
    # =========================================================
    # ENTRY
    # =========================================================
    #

    if progress <= 0.28:

        if significant_movement:

            return SkillPhaseResult(
                phase=PHASE_ENTRY,
                confidence=0.86,
                reason=(
                    'Frame occurs early in the movement and '
                    'shows significant body-position change '
                    'from the previous analyzed frame.'
                ),
            )

        return SkillPhaseResult(
            phase=PHASE_ENTRY,
            confidence=0.74,
            reason=(
                'Frame occurs within the early transition '
                'portion of the movement.'
            ),
        )


    #
    # =========================================================
    # HANDSTAND-SPECIFIC PEAK
    # =========================================================
    #
    # A handstand has a meaningful central hold/top position.
    #
    # Previous generic logic was too restrictive and often
    # classified every middle frame as main_action.
    #
    # For a Handstand we intentionally create a central Peak
    # window, then use body measurements and stability to
    # increase confidence.
    #

    if (
        normalized_skill
        == 'handstand'
    ):

        if (
            0.38
            <= progress
            <= 0.68
        ):

            confidence = 0.76

            reason_parts = [
                (
                    'Frame occurs within the central '
                    'Handstand peak window.'
                ),
            ]


            if straight_knees:

                confidence += 0.04

                reason_parts.append(
                    (
                        'The knees are relatively '
                        'extended.'
                    )
                )


            if open_hips:

                confidence += 0.04

                reason_parts.append(
                    (
                        'The hips are relatively open.'
                    )
                )


            if open_shoulders:

                confidence += 0.03

                reason_parts.append(
                    (
                        'The shoulders are relatively '
                        'open.'
                    )
                )


            if vertical_torso:

                confidence += 0.04

                reason_parts.append(
                    (
                        'The torso is relatively '
                        'vertical.'
                    )
                )


            if relatively_stable:

                confidence += 0.04

                reason_parts.append(
                    (
                        'Frame-to-frame movement is '
                        'relatively low.'
                    )
                )


            if (
                very_straight_knees
                and very_open_hips
                and very_vertical_torso
                and very_stable
            ):

                confidence = max(
                    confidence,
                    0.94,
                )

                reason_parts.append(
                    (
                        'The athlete shows a particularly '
                        'straight, vertical, and stable '
                        'Handstand position.'
                    )
                )


            confidence = min(
                confidence,
                0.95,
            )


            return SkillPhaseResult(
                phase=PHASE_PEAK,
                confidence=confidence,
                reason=' '.join(
                    reason_parts
                ),
            )


        #
        # Handstand frames between entry and peak.
        #
        if progress < 0.38:

            return SkillPhaseResult(
                phase=PHASE_MAIN_ACTION,
                confidence=0.78,
                reason=(
                    'Frame occurs after the Handstand '
                    'entry and before the central peak '
                    'position.'
                ),
            )


        #
        # Handstand frames immediately after peak.
        #
        if progress <= 0.82:

            return SkillPhaseResult(
                phase=PHASE_EXIT,
                confidence=0.82,
                reason=(
                    'Frame occurs after the central '
                    'Handstand peak and indicates the '
                    'athlete is leaving the primary '
                    'position.'
                ),
            )


    #
    # =========================================================
    # CAST HANDSTAND PEAK
    # =========================================================
    #

    if (
        normalized_skill
        == 'cast handstand'
    ):

        if (
            0.48
            <= progress
            <= 0.72
        ):

            confidence = 0.72

            reason_parts = [
                (
                    'Frame occurs within the central '
                    'Cast Handstand peak window.'
                ),
            ]


            if straight_knees:

                confidence += 0.04

                reason_parts.append(
                    'The knees are extended.'
                )


            if open_hips:

                confidence += 0.05

                reason_parts.append(
                    'The hips are open.'
                )


            if open_shoulders:

                confidence += 0.04

                reason_parts.append(
                    'The shoulders are open.'
                )


            if vertical_torso:

                confidence += 0.05

                reason_parts.append(
                    (
                        'The torso is relatively '
                        'vertical.'
                    )
                )


            if relatively_stable:

                confidence += 0.03

                reason_parts.append(
                    (
                        'Movement has reduced near '
                        'the top position.'
                    )
                )


            confidence = min(
                confidence,
                0.94,
            )


            return SkillPhaseResult(
                phase=PHASE_PEAK,
                confidence=confidence,
                reason=' '.join(
                    reason_parts
                ),
            )


    #
    # =========================================================
    # GENERIC PEAK POSITION
    # =========================================================
    #
    # Used for skills without a dedicated classifier.
    #

    if (
        0.28 < progress < 0.76
        and straight_knees
        and open_hips
        and vertical_torso
        and relatively_stable
    ):

        confidence = 0.86

        reasons = [
            (
                'Frame occurs in the central portion '
                'of the movement.'
            ),

            (
                'The body position is relatively stable '
                'compared with the previous frame.'
            ),

            (
                'Knee and hip measurements show a '
                'relatively straight body position.'
            ),

            (
                'The torso is relatively vertical.'
            ),
        ]


        if (
            very_straight_knees
            and very_open_hips
            and very_vertical_torso
            and very_stable
        ):

            confidence = 0.94

            reasons.append(
                (
                    'The body is especially straight, '
                    'vertical, and stable.'
                )
            )


        return SkillPhaseResult(
            phase=PHASE_PEAK,
            confidence=confidence,
            reason=' '.join(
                reasons
            ),
        )


    #
    # =========================================================
    # GENERIC FALLBACK PEAK
    # =========================================================
    #
    # Allows a lower-confidence Peak when the frame is
    # centrally located and shows at least one useful
    # peak-like body characteristic.
    #

    if (
        0.42
        <= progress
        <= 0.62
        and (
            straight_knees
            or open_hips
            or vertical_torso
        )
    ):

        confidence = 0.68

        reason_parts = [
            (
                'Frame occurs near the center of '
                'the movement sequence.'
            ),

            (
                'At least one body-position '
                'measurement supports a possible '
                'peak position.'
            ),
        ]


        if straight_knees:

            confidence += 0.03

            reason_parts.append(
                (
                    'The knees are relatively '
                    'extended.'
                )
            )


        if open_hips:

            confidence += 0.03

            reason_parts.append(
                (
                    'The hips are relatively open.'
                )
            )


        if vertical_torso:

            confidence += 0.03

            reason_parts.append(
                (
                    'The torso is relatively '
                    'vertical.'
                )
            )


        if relatively_stable:

            confidence += 0.03

            reason_parts.append(
                (
                    'Frame-to-frame movement is '
                    'relatively low.'
                )
            )


        confidence = min(
            confidence,
            0.82,
        )


        return SkillPhaseResult(
            phase=PHASE_PEAK,
            confidence=confidence,
            reason=' '.join(
                reason_parts
            ),
        )


    #
    # =========================================================
    # MAIN ACTION
    # =========================================================
    #

    if (
        progress <= 0.68
        and significant_movement
    ):

        confidence = (
            0.86
            if high_movement
            else 0.80
        )

        reason_parts = [
            (
                'Frame occurs in the central portion '
                'of the movement.'
            ),

            (
                'Significant frame-to-frame movement '
                'is occurring.'
            ),
        ]


        if hip_change is not None:

            if hip_change > 3:

                reason_parts.append(
                    (
                        'The hip angle is opening.'
                    )
                )

            elif hip_change < -3:

                reason_parts.append(
                    (
                        'The hip angle is closing.'
                    )
                )


        if knee_change is not None:

            if knee_change > 3:

                reason_parts.append(
                    (
                        'The knees are extending.'
                    )
                )

            elif knee_change < -3:

                reason_parts.append(
                    (
                        'The knees are bending.'
                    )
                )


        if shoulder_change is not None:

            if shoulder_change > 3:

                reason_parts.append(
                    (
                        'The shoulder angle is opening.'
                    )
                )

            elif shoulder_change < -3:

                reason_parts.append(
                    (
                        'The shoulder angle is closing.'
                    )
                )


        return SkillPhaseResult(
            phase=PHASE_MAIN_ACTION,
            confidence=confidence,
            reason=' '.join(
                reason_parts
            ),
        )


    #
    # Central frame with lower movement but without enough
    # evidence for Peak classification.
    #

    if progress <= 0.68:

        return SkillPhaseResult(
            phase=PHASE_MAIN_ACTION,
            confidence=0.68,
            reason=(
                'Frame occurs in the central movement '
                'window but does not meet the current '
                'peak-position criteria.'
            ),
        )


    #
    # =========================================================
    # EXIT
    # =========================================================
    #

    if progress <= 0.90:

        reason_parts = [
            (
                'Frame occurs after the primary central '
                'movement window.'
            ),
        ]

        confidence = 0.80


        if significant_movement:

            confidence = 0.86

            reason_parts.append(
                (
                    'Body position is still changing '
                    'significantly, indicating an exit '
                    'transition.'
                )
            )


        if torso_change is not None:

            if torso_change > 3:

                reason_parts.append(
                    (
                        'The torso orientation is moving '
                        'toward a more vertical position.'
                    )
                )

            elif torso_change < -3:

                reason_parts.append(
                    (
                        'The torso orientation is moving '
                        'away from vertical.'
                    )
                )


        return SkillPhaseResult(
            phase=PHASE_EXIT,
            confidence=confidence,
            reason=' '.join(
                reason_parts
            ),
        )


    #
    # =========================================================
    # FINISH
    # =========================================================
    #

    if relatively_stable:

        return SkillPhaseResult(
            phase=PHASE_FINISH,
            confidence=0.94,
            reason=(
                'Frame occurs near the end of the movement '
                'and body-position change has reduced.'
            ),
        )


    return SkillPhaseResult(
        phase=PHASE_FINISH,
        confidence=0.86,
        reason=(
            'Frame occurs near the end of the analyzed '
            'movement sequence.'
        ),
    )