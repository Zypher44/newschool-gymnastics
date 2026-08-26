from pathlib import Path

import cv2


POSE_CONNECTIONS = [
    ('left_shoulder', 'right_shoulder'),

    ('left_shoulder', 'left_elbow'),
    ('left_elbow', 'left_wrist'),

    ('right_shoulder', 'right_elbow'),
    ('right_elbow', 'right_wrist'),

    ('left_shoulder', 'left_hip'),
    ('right_shoulder', 'right_hip'),

    ('left_hip', 'right_hip'),

    ('left_hip', 'left_knee'),
    ('left_knee', 'left_ankle'),

    ('right_hip', 'right_knee'),
    ('right_knee', 'right_ankle'),
]


class PoseDrawingError(Exception):
    pass


def normalized_to_pixel(
    landmark,
    width,
    height,
):
    try:
        x = float(
            landmark['x']
        )

        y = float(
            landmark['y']
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    x = max(
        0.0,
        min(
            1.0,
            x,
        ),
    )

    y = max(
        0.0,
        min(
            1.0,
            y,
        ),
    )

    return (
        int(
            x * (
                width - 1
            )
        ),
        int(
            y * (
                height - 1
            )
        ),
    )


def draw_pose_overlay(
    image_path,
    output_path,
    landmarks,
    pose_angles=None,
):
    image_path = Path(
        image_path
    )

    output_path = Path(
        output_path
    )

    if not image_path.exists():
        raise PoseDrawingError(
            f'Image does not exist: {image_path}'
        )

    image = cv2.imread(
        str(image_path)
    )

    if image is None:
        raise PoseDrawingError(
            'OpenCV could not read the frame.'
        )

    height, width = image.shape[:2]

    print(
        'DRAWING IMAGE:',
        image_path,
        width,
        height,
    )

    print(
        'LANDMARK NAMES:',
        list(
            landmarks.keys()
        ),
    )

    pixel_points = {}

    for name, landmark in landmarks.items():

        point = normalized_to_pixel(
            landmark,
            width,
            height,
        )

        if point is None:
            continue

        pixel_points[name] = point

        print(
            name,
            landmark.get('x'),
            landmark.get('y'),
            '->',
            point,
        )


    #
    # Giant diagnostic banner.


    #
    # Skeleton connections.
    #
    for start_name, end_name in POSE_CONNECTIONS:

        start = pixel_points.get(
            start_name
        )

        end = pixel_points.get(
            end_name
        )

        if start is None or end is None:
            continue

        cv2.line(
            image,
            start,
            end,
            (255, 0, 255),
            10,
            cv2.LINE_AA,
        )


    #
    # Joint points.
    #
    for name, point in pixel_points.items():

        cv2.circle(
            image,
            point,
            14,
            (0, 255, 255),
            -1,
            cv2.LINE_AA,
        )

        cv2.circle(
            image,
            point,
            14,
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )


    #
    # Joint angles.
    #
    pose_angles = (
        pose_angles
        or {}
    )

    angle_locations = {
        'left_elbow_angle': 'left_elbow',
        'right_elbow_angle': 'right_elbow',

        'left_shoulder_angle': 'left_shoulder',
        'right_shoulder_angle': 'right_shoulder',

        'left_hip_angle': 'left_hip',
        'right_hip_angle': 'right_hip',

        'left_knee_angle': 'left_knee',
        'right_knee_angle': 'right_knee',
    }

    for angle_name, value in pose_angles.items():

        joint_name = angle_locations.get(
            angle_name
        )

        if not joint_name:
            continue

        point = pixel_points.get(
            joint_name
        )

        if point is None:
            continue

        x, y = point

        label = (
            f'{value} deg'
        )

        cv2.putText(
            image,
            label,
            (
                x + 15,
                y - 15,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            5,
            cv2.LINE_AA,
        )

        cv2.putText(
            image,
            label,
            (
                x + 15,
                y - 15,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )


    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    success = cv2.imwrite(
        str(output_path),
        image,
    )

    if not success:
        raise PoseDrawingError(
            (
                'OpenCV could not save '
                f'{output_path}'
            )
        )

    print(
        'ANNOTATED IMAGE SAVED:',
        output_path,
        output_path.stat().st_size,
        'bytes',
    )

    return str(
        output_path
    )