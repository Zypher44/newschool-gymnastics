from django import template
from video_library.views import user_is_coach

register = template.Library()


@register.inclusion_tag('video_library/components/video_moments_panel.html', takes_context=True)
def video_moments_panel(context, video, user, player_id):
    return dict(video=video, is_coach=user_is_coach(user), player_id=player_id,
                request=context.get('request'), csrf_token=context.get('csrf_token'))
