"""Summaries from stored frame evidence, without synthetic recognition scores."""
from collections import defaultdict
from .results import AnalysisEngineResult
from .skill_rules import get_rule_set


class EvidenceAnalysisEngine:
    source = 'pose'
    version = 'pose-evidence-1.0.0'

    def analyze(self, analysis):
        frames = list(analysis.moments.exclude(frame_image='').order_by('timestamp_seconds'))
        angles = defaultdict(list)
        usable = detected = 0
        for frame in frames:
            data = frame.measurements or {}
            if not data.get('pose_detected'):
                continue
            detected += 1
            if data.get('pose_angles'):
                usable += 1
            for name, value in (data.get('pose_angles') or {}).items():
                angles[name].append(float(value))
        skill = (analysis.requested_skill or analysis.video.skill_name or '').strip()
        camera_view = (analysis.raw_results or {}).get('camera_view', analysis.video.camera_view)
        supported = get_rule_set(skill) is not None
        technique_available = supported and camera_view == 'side'
        strengths, improvements = [], []
        observations = analysis.moments.filter(label__startswith='Skill Observation:').order_by('timestamp_seconds') if technique_available else []
        for moment in observations:
            target = strengths if moment.severity == 'positive' else improvements
            if moment.description and moment.description not in target:
                target.append(moment.description)
        if not detected:
            summary = 'No usable athlete pose was detected. Record a clear view of one athlete with the whole body visible.'
        elif not usable:
            summary = 'An athlete was detected, but the required joints were not visible enough to measure. Coach review is needed.'
        else:
            summary = f'Pose detected in {detected} of {len(frames)} sampled frames; visible joint angles measured in {usable} frames. '
            if technique_available:
                summary += 'Cast handstand rule observations are available for coach review.'
            elif supported:
                summary += 'A confirmed side view is required for joint-angle technique cues; manual coach review is needed.'
            else:
                summary += 'Dedicated technique rules are not available for the selected skill; manual coach review is needed.'
        summary += ' Measurements are projected image angles, affected by camera view. Skill selection is supplied by the coach.'
        return AnalysisEngineResult(
            detected_skill='', skill_confidence=None, summary=summary,
            strengths=strengths[:5], improvements=improvements[:5],
            measurements={
                'sampled_frames': len(frames), 'frames_with_pose': detected,
                'frames_with_joint_angles': usable,
                'average_joint_angles_degrees': {name: round(sum(values) / len(values), 1) for name, values in angles.items()},
                'joint_angle_sample_counts': {name: len(values) for name, values in angles.items()},
                'measurement_space': 'image_plane_height_units_v2',
            },
            raw_results={'mock_analysis': False, 'selected_skill': skill, 'skill_rule_supported': supported,
                         'camera_view': camera_view, 'technique_available': technique_available,
                         'coach_review_required': True, 'engine': type(self).__name__},
            moments=[],
        )
