"""Read-only coaching summaries grounded in current saved frame evidence."""
import math
from .skill_rules import get_rule_set

CUES = {
    'cast_entry_knee_bend': ('Leg line at the start', 'The sampled image suggests bent knees during the estimated entry.', 'Keep your legs long as you start the cast.'),
    'cast_hip_closure': ('Body line through the cast', 'The sampled image suggests a closed hip position during the estimated cast phase.', 'Keep your body long through the cast.'),
    'cast_shoulder_angle': ('Shoulder opening', 'The sampled image suggests limited shoulder opening during the estimated cast phase.', 'Reach tall through your shoulders.'),
    'cast_straight_legs': ('Straight legs', 'The legs appear nearly straight in this sampled image.', ''),
    'cast_peak_alignment': ('Open body line', 'The hip and shoulder measurements suggest an open body line near the estimated peak.', ''),
}
PHASES = {'setup': 'Setup', 'entry': 'Entry', 'main_action': 'Main action', 'peak': 'Peak', 'exit': 'Exit', 'finish': 'Finish'}


def _dict(value):
    return value if isinstance(value, dict) else {}


def _number(value, maximum=None):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum) else None


def _timestamp(value):
    return f'{int(value // 60)}:{value % 60:05.2f}'


def _frame_item(frame):
    seconds = _number(frame.timestamp_seconds)
    return {'frame': frame, 'seconds': seconds, 'time': _timestamp(seconds),
            'phase': PHASES.get(_dict(frame.measurements).get('skill_phase'), 'Review point')}


def build_coaching_brief(analysis):
    if not analysis or analysis.status != 'completed' or analysis.analysis_source == 'mock':
        return None
    raw = _dict(analysis.raw_results)
    skill = raw.get('selected_skill') or analysis.requested_skill or 'Unspecified skill'
    rule = get_rule_set(skill)
    current = analysis.analysis_source == 'pose' and analysis.analysis_version == 'pose-evidence-1.0.0'
    side = raw.get('camera_view') == 'side'
    moments = list(analysis.moments.all())
    frames = sorted((m for m in moments if m.frame_image and _number(m.timestamp_seconds) is not None),
                    key=lambda m: (float(m.timestamp_seconds), m.pk))
    source_frames = {m.pk: m for m in frames}
    pose_frames = [m for m in frames if _dict(m.measurements).get('pose_detected') is True]
    measured = sum(any(_number(value, 180) is not None for value in _dict(_dict(m.measurements).get('pose_angles')).values()) for m in pose_frames)
    groups = {}
    if current and side and rule:
        for moment in moments:
            data = _dict(moment.measurements)
            code = data.get('observation_code')
            if not moment.label.startswith('Skill Observation:') or code not in CUES or data.get('rule_version') != rule.rule_version:
                continue
            source = source_frames.get(data.get('source_frame_moment_id'))
            if source is None or _number(moment.timestamp_seconds) != _number(source.timestamp_seconds):
                continue
            frame_data = _dict(source.measurements)
            if frame_data.get('pose_detected') is not True or data.get('skill_phase') != frame_data.get('skill_phase'):
                continue
            visibility = _number(_dict(frame_data.get('gymnastics_measurements')).get('average_landmark_visibility'), 1)
            phase_confidence = _number(frame_data.get('skill_phase_confidence'), 1)
            if visibility is None or phase_confidence is None or visibility < rule.minimum_pose_visibility or phase_confidence < rule.minimum_phase_confidence:
                continue
            try:
                candidates = rule.evaluate_frame(phase=frame_data.get('skill_phase'), measurements=frame_data)
            except (TypeError, ValueError, AttributeError, OverflowError):
                continue
            observed = next((candidate for candidate in candidates if candidate.code == code and candidate.severity == moment.severity), None)
            if observed is None:
                continue
            values = [(name.replace('_', ' ').capitalize(), _number(value, 180)) for name, value in observed.measurements.items()]
            if not values or any(value is None for _, value in values):
                continue
            title, observation, cue = CUES[code]
            group = groups.setdefault(code, {'code': code, 'title': title, 'observation': observation, 'cue': cue,
                                              'positive': observed.severity == 'positive', 'sources': {}, 'quality': -1})
            group['sources'][source.pk] = source
            quality = visibility + phase_confidence
            if quality > group['quality']:
                group.update(_frame_item(source))
                group['values'] = [(name, round(value, 1)) for name, value in values]
                group['quality'] = quality
    for group in groups.values():
        group['count'] = len(group['sources'])
    ordered = sorted(groups.values(), key=lambda item: (-item['count'], item['seconds'], item['code']))
    priorities = [item for item in ordered if not item['positive']][:2]
    strengths = [item for item in ordered if item['positive']][:2]
    checkpoints = []
    if current:
        candidates = [m for m in pose_frames if _dict(m.measurements).get('is_key_frame') is True] or pose_frames
        seen = set()
        for frame in candidates:
            phase = _dict(frame.measurements).get('skill_phase')
            if phase in seen:
                continue
            seen.add(phase)
            checkpoints.append(_frame_item(frame))
            if len(checkpoints) == 4:
                break
    if not current:
        status, guidance = 'Run a fresh analysis', 'This report uses an older analysis format. Run a new analysis before using technique cues.'
    elif not frames or not pose_frames:
        status, guidance = 'A clearer recording is needed', 'Record one athlete with the whole body visible and good lighting, then run a new analysis.'
    elif not rule:
        status, guidance = 'Coach review needed', f'Dedicated technique rules are not available for {skill}. Use the review points below and record your own feedback.'
    elif not side:
        status, guidance = 'Confirm the recording view', 'Technique cues require a side view. Set the camera view on the video page, then run a new analysis.'
    elif priorities or strengths:
        status, guidance = 'Technique observations to review', 'Review the highlighted frames before choosing one cue for the next turn. These are sampled image measurements; phases are estimates.'
    else:
        status, guidance = 'Review the key moments', 'No technique cues met the evidence requirements. This does not establish that the skill was correct; review the video and add your own feedback.'
    draft = ['Coach review draft — verify against the video', f'Skill: {skill}']
    if priorities:
        first = priorities[0]
        draft += [f'Possible focus: {first["title"]} at {first["time"]}.', f'Suggested athlete cue: {first["cue"]}']
    if strengths:
        first = strengths[0]
        draft += [f'What worked: {first["observation"]} Review {first["time"]}.']
    if not priorities and not strengths:
        draft += ['Manual review: add one strength and one focus after watching the video.']
    draft += ['Next practice: choose one focus and a suitable drill.', 'Coach-selected drill:', 'Goal for the next attempt:']
    return {'skill': skill, 'status': status, 'guidance': guidance, 'sampled': len(frames), 'detected': len(pose_frames),
            'measured': measured, 'priorities': priorities, 'strengths': strengths, 'checkpoints': checkpoints,
            'draft': '\n'.join(draft), 'technique_available': current and bool(rule) and side}
