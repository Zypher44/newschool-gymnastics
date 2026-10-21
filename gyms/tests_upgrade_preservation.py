"""Rehearse the September production schema -> October release on synthetic data."""
from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ProductionUpgradePreservationTests(TransactionTestCase):
    def test_legacy_accounts_scores_surveys_links_and_media_references_survive(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old = dict(latest)
        old.update({
            'accounts': '0003_user_phone_copy_profile_phones',
            'gyms': '0001_initial',
            'parents_portal': '0002_alter_parentathletelink_approved_and_more',
            'routine_tracker': '0003_session_gym',
            'surveys': '0002_alter_dailysurvey_energy_alter_dailysurvey_soreness_and_more',
            'video_library': '0010_video_gym',
            'practice_focus': None, 'skill_tracker': None,
            'practice_hub': None, 'gym_scheduling': None,
        })
        targets = list(old.items())
        try:
            executor.migrate(targets)
            apps = executor.loader.project_state([target for target in targets if target[1] is not None]).apps
            User = apps.get_model('accounts', 'User')
            coach = User.objects.create(username='upgrade-coach', role='head_coach', password='unchanged-fixture-hash')
            athlete = User.objects.create(username='upgrade-athlete', role='athlete', password='athlete-fixture-hash')
            parent = User.objects.create(username='upgrade-parent', role='parent', password='parent-fixture-hash')
            gym = apps.get_model('gyms', 'Gym').objects.create(name='Upgrade fixture gym')
            for user in [coach, athlete, parent]:
                apps.get_model('gyms', 'GymMembership').objects.create(gym=gym, user=user, role=user.role)
            apps.get_model('athletes', 'AthleteProfile').objects.create(user=athlete, date_of_birth=date(2015, 1, 2))
            apps.get_model('athletes', 'AttendanceRecord').objects.create(athlete=athlete, coach=coach,
                attendance_date=date(2026, 9, 28), status='present', notes='Preserve attendance fixture')
            apps.get_model('parents_portal', 'ParentAthleteLink').objects.create(parent=parent,
                athlete=athlete, approved=True, relationship='Guardian')
            Session = apps.get_model('routine_tracker', 'DailyRoutineSession')
            Attempt = apps.get_model('routine_tracker', 'DailyRoutineAttempt')
            session = Session.objects.create(gym=gym, practice_date=date(2026, 9, 28), created_by=coach)
            for number, result in enumerate(['wow', 'hit', 'missed'], 1):
                Attempt.objects.create(session=session, athlete=athlete, event='beam',
                    attempt_number=number, result=result, recorded_by=coach, notes='Preserve score fixture')
            apps.get_model('surveys', 'DailySurvey').objects.create(athlete=athlete,
                survey_date=date(2026, 9, 28), energy=4, soreness=2, stress=3,
                sleep_hours='8.5', ate_well=True, hydrated=True, notes='Preserve old survey')
            apps.get_model('video_library', 'Video').objects.create(gym=gym, title='Legacy video fixture',
                video_file='videos/2026/09/legacy-fixture.mp4', thumbnail='thumbnails/legacy-fixture.jpg',
                uploaded_by=coach, primary_athlete=athlete, visibility='parents', status='ready')
            level = apps.get_model('pathway', 'PathwayLevel').objects.create(name='Upgrade fixture level', code='upgrade-fixture')
            apps.get_model('pathway', 'AthletePathway').objects.create(athlete=athlete,
                current_level=level, managed_by=coach, head_coach_notes='Keep pathway notes')
            labels = [('accounts','User'), ('gyms','Gym'), ('gyms','GymMembership'),
                ('athletes','AthleteProfile'), ('athletes','AttendanceRecord'),
                ('parents_portal','ParentAthleteLink'), ('routine_tracker','DailyRoutineSession'),
                ('routine_tracker','DailyRoutineAttempt'), ('surveys','DailySurvey'),
                ('video_library','Video'), ('pathway','AthletePathway')]
            snapshots = {}
            for label in labels:
                model = apps.get_model(*label)
                fields = [field.attname for field in model._meta.concrete_fields]
                snapshots[label] = (fields, list(model.objects.order_by('pk').values(*fields)))
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            new_apps = executor.loader.project_state(latest).apps
            for label, (fields, expected) in snapshots.items():
                with self.subTest(model=label):
                    actual = list(new_apps.get_model(*label).objects.order_by('pk').values(*fields))
                    self.assertEqual(actual, expected)
            self.assertFalse(new_apps.get_model('routine_tracker','DailyRoutineAttempt').objects.filter(is_pressure=True).exists())
            self.assertEqual(new_apps.get_model('surveys','DailySurvey').objects.get(athlete_id=athlete.pk).checkin_version, 1)
        finally:
            MigrationExecutor(connection).migrate(latest)
