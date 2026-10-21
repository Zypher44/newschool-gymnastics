from django.apps import AppConfig

class SkillTrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'skill_tracker'

    def ready(self):
        from . import signals  # noqa: F401
