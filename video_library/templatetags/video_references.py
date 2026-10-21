from django import template
from video_library.reference_examples import get_coaching_examples
from video_library.ai.skill_interpretation import normalize_skill_name

register = template.Library()


@register.simple_tag
def coaching_reference_videos(video, user):
    return get_coaching_examples(video, user)


@register.simple_tag
def coaching_reference_pair(first_video, second_video, user):
    return get_coaching_examples(second_video, user).filter(pk=first_video.pk).exists()


@register.simple_tag
def matching_skill_pair(first_video, second_video):
    first_skill = normalize_skill_name(first_video.skill_name)
    second_skill = normalize_skill_name(second_video.skill_name)
    return bool(first_skill and first_skill == second_skill and first_video.event and first_video.event == second_video.event)
