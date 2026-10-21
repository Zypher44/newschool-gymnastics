"""Image-plane coordinates, scaled consistently and filtered by visibility."""
import math


def image_plane_landmarks(landmarks, width, height, *, minimum_visibility=0.60):
    if width <= 0 or height <= 0:
        raise ValueError('Image dimensions are required for pose measurements.')
    result = {}
    for name, point in landmarks.items():
        try:
            x, y = float(point['x']), float(point['y'])
            visibility = float(point.get('visibility') or 0)
            presence = point.get('presence')
            if not all(math.isfinite(v) for v in (x, y, visibility)):
                continue
            if visibility < minimum_visibility or (presence is not None and (not math.isfinite(float(presence)) or float(presence) < minimum_visibility)):
                continue
            result[name] = dict(point, x=x * width / height, y=y)
        except (KeyError, TypeError, ValueError):
            continue
    return result
