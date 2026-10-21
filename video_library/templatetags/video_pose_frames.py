from django import template

register = template.Library()


def picture_for(moment):
    data = moment.measurements if isinstance(moment.measurements, dict) else {}
    real = moment.analysis.analysis_source != 'mock'
    # A stored annotated file is sufficient; older records may lack the extra
    # generation flag. An explicit failed detection still invalidates it.
    overlay = bool(real and moment.annotated_frame_image and data.get('pose_detected') is not False)
    reason = ''
    if not overlay:
        if data.get('pose_detected') is False:
            reason = 'No athlete pose was detected in this frame.'
        elif real and data.get('pose_detected') is True:
            reason = 'Skeleton image is missing. Generate skeletons from a fresh pose analysis.'
        else:
            reason = 'No saved skeleton is available for this frame.'
    return {'overlay': overlay, 'image': moment.annotated_frame_image if overlay else moment.frame_image, 'reason': reason}


@register.simple_tag
def pose_frame_picture(moment):
    return picture_for(moment)


@register.simple_tag
def missing_pose_skeletons(analysis):
    if not analysis or analysis.status != 'completed' or analysis.analysis_source == 'mock':
        return False
    return any(moment.frame_image and not picture_for(moment)['overlay'] for moment in analysis.moments.all())
