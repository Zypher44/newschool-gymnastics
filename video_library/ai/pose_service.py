from PIL import Image
from .geometry import image_plane_landmarks
from .gymnastics_measurements import calculate_gymnastics_measurements
from .measurements import calculate_pose_angles
from .storage_files import local_storage_file

IMPORTANT_LANDMARKS = {f'{side}_{joint}' for side in ('left', 'right') for joint in ('shoulder', 'elbow', 'wrist', 'hip', 'knee', 'ankle')}
DERIVED_KEYS = {'pose_landmarks', 'pose_angles', 'gymnastics_measurements', 'motion_metrics', 'skill_phase', 'skill_phase_confidence', 'skill_phase_reason', 'analysis_quality', 'frame_score', 'frame_quality_score', 'frame_quality_reasons', 'key_frame_reason', 'is_key_frame'}


def analyze_extracted_frames(analysis, *, engine=None):
    if engine is None:
        from .pose import MediaPipePoseEngine
        engine = MediaPipePoseEngine()
    analyzed_count = detected_count = 0
    try:
        for moment in analysis.moments.exclude(frame_image='').order_by('timestamp_seconds'):
            measurements = {k: v for k, v in (moment.measurements or {}).items() if k not in DERIVED_KEYS}
            if moment.annotated_frame_image:
                moment.annotated_frame_image.delete(save=False)
            with local_storage_file(moment.frame_image, maximum_bytes=25 * 1024 * 1024) as path:
                with Image.open(path) as image:
                    width, height = image.size
                result = engine.analyze_image(path)
            analyzed_count += 1
            landmarks = {}
            if result.detected:
                detected_count += 1
                landmarks = {landmark.name: {
                    'x': round(landmark.x, 6), 'y': round(landmark.y, 6), 'z': round(landmark.z, 6),
                    'visibility': landmark.visibility, 'presence': getattr(landmark, 'presence', None),
                } for landmark in result.landmarks if landmark.name in IMPORTANT_LANDMARKS}
            scaled = image_plane_landmarks(landmarks, width, height)
            angles = calculate_pose_angles(scaled) if scaled else {}
            gymnastics = calculate_gymnastics_measurements(scaled, angles) if scaled else {}
            measurements.update({
                'pose_engine': 'mediapipe', 'pose_detected': result.detected,
                'pose_landmark_count': result.landmark_count if result.detected else 0,
                'pose_landmarks': landmarks, 'pose_angles': angles, 'gymnastics_measurements': gymnastics,
                'image_width': width, 'image_height': height, 'measurement_space': 'image_plane_height_units_v2',
                'measurement_limitations': 'Projected image angles; camera perspective affects measurements.',
            })
            moment.measurements = measurements
            moment.save(update_fields=['measurements', 'annotated_frame_image', 'updated_at'])
    finally:
        engine.close()
    return {'analyzed_frames': analyzed_count, 'frames_with_pose': detected_count}
