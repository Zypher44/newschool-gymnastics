from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import PublicSignUpForm


def home(request):
    if request.user.is_authenticated:
        return redirect('role_redirect')

    return render(
        request,
        'home.html',
    )


def signup(request):
    if request.user.is_authenticated:
        return redirect('role_redirect')

    if request.method == 'POST':
        form = PublicSignUpForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(
                request,
                user,
            )

            messages.success(
                request,
                'Your NewSchool Gymnastics account has been created.',
            )

            return redirect('role_redirect')

    else:
        form = PublicSignUpForm()

    return render(
        request,
        'registration/signup.html',
        {
            'form': form,
        },
    )