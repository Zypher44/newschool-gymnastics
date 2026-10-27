from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def safety_support(request):
    return render(request, 'communications/safety_support.html', {
        'layout': 'base.html' if request.user.is_authenticated else 'public_base.html',
    })
