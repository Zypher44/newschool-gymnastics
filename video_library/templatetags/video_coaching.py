from django import template
from video_library.ai.coaching_brief import build_coaching_brief

register = template.Library()


@register.simple_tag
def video_coaching_brief(analysis):
    return build_coaching_brief(analysis)
