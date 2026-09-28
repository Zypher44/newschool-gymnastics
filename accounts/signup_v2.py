"""Public gym registration. Memberships stay pending until a director approves them."""

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.shortcuts import redirect, render

from gyms.models import Gym, GymMembership


User = get_user_model()


class SignupBaseForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class DirectorSignupForm(SignupBaseForm):
    gym_name = forms.CharField(max_length=150, label='Gym name',
                               widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_gym_name(self):
        name = self.cleaned_data['gym_name'].strip()
        if not name:
            raise forms.ValidationError('Enter the name of your gym.')
        return name


class MemberSignupForm(SignupBaseForm):
    role = forms.ChoiceField(choices=[
        ('athlete', 'Athlete'), ('parent', 'Parent or Guardian'), ('coach', 'Coach')
    ], widget=forms.RadioSelect())
    gym = forms.ModelChoiceField(
        queryset=Gym.objects.none(), empty_label='Select your gym',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Your director will approve your request before you can access gym information.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gym'].queryset = Gym.objects.filter(is_active=True).order_by('name', 'pk')


def director_signup(request):
    if request.user.is_authenticated:
        return redirect('role_redirect')
    form = DirectorSignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.role = 'director'
            user.save()
            gym = Gym.objects.create(name=form.cleaned_data['gym_name'])
            GymMembership.objects.create(gym=gym, user=user, role='director', is_active=True)
        login(request, user)
        messages.success(request, 'Your gym has been created. Add its details in Gym Settings.')
        return redirect('director_dashboard')
    return render(request, 'registration/director_signup.html', {'form': form})


def member_signup(request):
    if request.user.is_authenticated:
        return redirect('role_redirect')
    form = MemberSignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.role = form.cleaned_data['role']
            user.save()
            GymMembership.objects.create(
                gym=form.cleaned_data['gym'], user=user,
                role=user.role, is_active=False,
            )
        login(request, user)
        messages.success(request, 'Your request was sent to the gym director for approval.')
        return redirect('role_redirect')
    return render(request, 'registration/member_signup.html', {'form': form})
