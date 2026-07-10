from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import ParentProfile, ParentAthleteLink

admin.site.register(ParentProfile)
admin.site.register(ParentAthleteLink)