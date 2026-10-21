from django import template
from practice_focus.report_preferences import CoachReportPreferenceForm, report_gym_id, show_group_averages

register = template.Library()


@register.inclusion_tag('practice_focus/report_settings_card.html', takes_context=True)
def coach_report_preferences(context):
    request = context.get('request')
    available = bool(request and report_gym_id(request.user) is not None)
    form = CoachReportPreferenceForm(
        prefix='reports', initial={'show_group_averages': show_group_averages(request.user)},
    ) if available else None
    return {'available': available, 'form': form, 'csrf_token': context.get('csrf_token')}
