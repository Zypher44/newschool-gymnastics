"""Conservative picture comparisons from the exact saved frame landmarks."""
from .aligned_timing import aligned_timing, number
from .measurements import calculate_angle
from .skill_interpretation import normalize_skill_name

JOINTS = {
    'shoulder': ('hip', 'shoulder', 'elbow'),
    'hip': ('shoulder', 'hip', 'knee'),
    'knee': ('hip', 'knee', 'ankle'),
    'elbow': ('shoulder', 'elbow', 'wrist'),
}
MIN_VISIBILITY = .65
MIN_PHASE = .70


def dictionary(value):
    return value if isinstance(value, dict) else {}


def frame_evidence(point, phase):
    frame = point.get('frame_moment')
    if not frame or not frame.frame_image:
        return None
    analysis = frame.analysis
    data = dictionary(frame.measurements)
    confidence = number(data.get('skill_phase_confidence'), 1)
    visibility = number(dictionary(data.get('gymnastics_measurements')).get('average_landmark_visibility'), 1)
    width, height = number(data.get('image_width'), 16384), number(data.get('image_height'), 16384)
    if (analysis.status != 'completed' or analysis.analysis_source != 'pose'
            or analysis.analysis_version != 'pose-evidence-1.0.0'
            or dictionary(analysis.raw_results).get('camera_view') != 'side'
            or data.get('pose_detected') is not True or data.get('skill_phase') != phase
            or data.get('measurement_space') != 'image_plane_height_units_v2'
            or confidence is None or confidence < MIN_PHASE or visibility is None or visibility < MIN_VISIBILITY
            or not width or not height
            or number(point.get('timestamp')) != number(frame.timestamp_seconds)):
        return None
    return {'data': data, 'width': width, 'height': height, 'confidence': confidence}


def joint_evidence(evidence, side, joint):
    landmarks = dictionary(evidence['data'].get('pose_landmarks'))
    points, visibilities = [], []
    for name in JOINTS[joint]:
        landmark = dictionary(landmarks.get(f'{side}_{name}'))
        x, y = number(landmark.get('x'), 1), number(landmark.get('y'), 1)
        visibility = number(landmark.get('visibility'), 1)
        presence = landmark.get('presence')
        if (x is None or y is None or visibility is None or visibility < MIN_VISIBILITY
                or (presence is not None and (number(presence, 1) is None or number(presence, 1) < MIN_VISIBILITY))):
            return None
        points.append({'x': x * evidence['width'], 'y': y * evidence['height']})
        visibilities.append(visibility)
    angle = calculate_angle(*points)
    if angle is None:
        return None
    return {'angle': angle, 'points': points, 'vertex': points[1],
            'line': ' '.join(f'{p["x"]:.3f},{p["y"]:.3f}' for p in points),
            'width': evidence['width'], 'height': evidence['height'],
            'radius': max(4, min(evidence['width'], evidence['height']) * .02),
            'visibility': min(visibilities), 'confidence': evidence['confidence']}


def build_comparison_insights(phases, first_video, second_video, first_analysis, second_analysis, *, matching, example):
    valid_pair = bool(matching and first_video.gym_id == second_video.gym_id)
    pictures, comparisons, timing_phases = [], [], []
    for phase in phases:
        if not phase.get('first') or not phase.get('second'):
            continue
        picture = dict(phase, highlight=None)
        pictures.append(picture)
        if not valid_pair or not first_analysis or not second_analysis:
            continue
        frame_a, frame_b = phase['first'].get('frame_moment'), phase['second'].get('frame_moment')
        if not frame_a or not frame_b or frame_a.analysis_id != first_analysis.pk or frame_b.analysis_id != second_analysis.pk:
            continue
        if first_analysis.video_id != first_video.pk or second_analysis.video_id != second_video.pk:
            continue
        snapshots = [dictionary(a.raw_results).get('selected_skill') or a.requested_skill or a.detected_skill for a in (first_analysis, second_analysis)]
        if any(not isinstance(name, str) or not name or normalize_skill_name(name) != normalize_skill_name(video.skill_name) for name, video in zip(snapshots, (first_video, second_video))):
            continue
        first = frame_evidence(phase['first'], phase['name'])
        second = frame_evidence(phase['second'], phase['name'])
        if not first or not second:
            continue
        timing_phases.append(phase)
        choices = []
        for joint in JOINTS:
            for side in ('left', 'right'):
                a, b = joint_evidence(first, side, joint), joint_evidence(second, side, joint)
                if not a or not b:
                    continue
                gap = abs(b['angle'] - a['angle'])
                item = {'phase': phase['name'], 'phase_label': phase['label'], 'joint': joint, 'side': side,
                        'label': f'{side.title()} {joint}', 'first': a, 'second': b,
                        'gap': round(gap, 1), 'first_time': phase['first']['timestamp'],
                        'second_time': phase['second']['timestamp'],
                        'evidence_label': 'Clear joint visibility' if min(a['visibility'], b['visibility']) >= .85 else 'Usable joint visibility'}
                comparisons.append(item)
                choices.append(item)
        if choices:
            picture['highlight'] = max(choices, key=lambda c: c['gap'])
    timing = aligned_timing(timing_phases) if valid_pair else {'rows': [], 'starts': None, 'reason': 'Select the same skill and event to compare timing.'}
    # Interpret proximity to the selected example only. It is not a judging score.
    focus = max((c for c in comparisons if c['gap'] >= 5), key=lambda c: c['gap'], default=None) if example else None
    strength = min((c for c in comparisons if c['gap'] <= 5), key=lambda c: c['gap'], default=None) if example else None
    if focus:
        cue = f'With your coach, practise matching the {focus["joint"]} shape at {focus["phase_label"].lower()}.'
    else:
        cue = 'Watch the paired frames with your coach and choose one adjustment for the next turn.'
    draft = ['Comparison review draft — verify against both clips', f'Skill: {second_video.skill_name}',
             f'{"Example" if example else "Comparison A"}: {first_video.title}', f'Attempt: {second_video.title}']
    if focus:
        draft.append(f'Possible focus: {focus["label"]} at estimated {focus["phase_label"]}; A {focus["first"]["angle"]}°, B {focus["second"]["angle"]}°, difference {focus["gap"]}°. Review A {focus["first_time"]}s and B {focus["second_time"]}s.')
    if strength:
        draft.append(f'Similar shape: {strength["label"]} at estimated {strength["phase_label"]} (difference {strength["gap"]}°). This does not establish that the skill was correct.')
    draft.extend([f'Possible athlete cue: {cue}', 'Coach-selected drill:', 'Goal for the next attempt:'])
    # The client may set skill starts even if an Entry estimate is unavailable.
    manual_phases = [dict(p) for p in timing_phases if p['name'] in ('main_action', 'peak', 'exit', 'finish')]
    if valid_pair and not manual_phases:
        timing['reason'] = 'Both clips need supported sampled phases before timing can be compared. Run fresh side-view analyses or review the videos manually.'
    for phase in manual_phases:
        row = next((r for r in timing['rows'] if r['phase'] == phase['name']), None)
        phase['elapsed'] = row
    return {'phases': pictures, 'focus': focus, 'strength': strength, 'cue': cue, 'draft': '\n'.join(draft),
            'timing': timing, 'manual_phases': manual_phases, 'example': example,
            'available': bool(comparisons), 'paired_count': len(pictures),
            'measured_count': sum(p['highlight'] is not None for p in pictures)}
