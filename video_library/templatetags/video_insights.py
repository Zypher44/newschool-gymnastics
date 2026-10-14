from django import template
from video_library.ai.comparison_insights import build_comparison_insights

register = template.Library()


@register.simple_tag(takes_context=True)
def video_comparison_insights(context):
    return build_comparison_insights(context.get('phase_comparisons', []), context['first_video'],
                                    context['second_video'], context.get('first_analysis'), context.get('second_analysis'),
                                    matching=context.get('matching_pair'), example=context.get('example_comparison'))
