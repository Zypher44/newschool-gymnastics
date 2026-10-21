import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from gyms.models import Gym, GymMembership
from .models import DailyRoutineAttempt, DailyRoutineSession


class SaveRoutinePracticeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gym = Gym.objects.create(name='Routine test gym')
        self.coach = User.objects.create_user('routine_coach', password='pass', role='coach')
        self.athlete = User.objects.create_user('routine_athlete', password='pass', role='athlete')
        GymMembership.objects.create(gym=self.gym, user=self.coach, role='coach')
        GymMembership.objects.create(gym=self.gym, user=self.athlete, role='athlete')
        self.session = DailyRoutineSession.objects.create(
            gym=self.gym, practice_date=date(2026, 9, 30), created_by=self.coach,
        )
        self.client.force_login(self.coach)

    def test_saves_multiple_regular_and_pressure_attempts_together(self):
        response = self.client.post(
            reverse('routine_tracker:save_routine_practice'),
            data=json.dumps({
                'session_id': self.session.pk,
                'operations': [
                    {'athlete_id': self.athlete.pk, 'event': 'beam', 'result': 'hit', 'is_pressure': False},
                    {'athlete_id': self.athlete.pk, 'event': 'beam', 'result': 'wow', 'is_pressure': True},
                ],
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True, 'saved': 2, 'deleted': 0})
        self.assertEqual(DailyRoutineAttempt.objects.filter(session=self.session).count(), 2)
        self.assertTrue(DailyRoutineAttempt.objects.get(result='wow').is_pressure)

    def test_rejects_attempt_for_athlete_in_another_gym(self):
        foreign_gym = Gym.objects.create(name='Other gym')
        outsider = get_user_model().objects.create_user('outsider_athlete', role='athlete')
        GymMembership.objects.create(gym=foreign_gym, user=outsider, role='athlete')
        response = self.client.post(
            reverse('routine_tracker:save_routine_practice'),
            data=json.dumps({
                'session_id': self.session.pk,
                'operations': [
                    {'athlete_id': outsider.pk, 'event': 'beam', 'result': 'hit', 'is_pressure': True},
                ],
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(DailyRoutineAttempt.objects.filter(session=self.session).count(), 0)


class RoutineGroupQuickComparisonTests(TestCase):
    def test_summary_compares_athlete_with_assigned_group_peers(self):
        from datetime import date

        from gyms.models import TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach
        from .views import build_group_quick_comparison

        User = get_user_model()
        gym = Gym.objects.create(name='Routine comparison gym')
        coach = User.objects.create_user('comparison_coach', password='pass', role='coach')
        athlete = User.objects.create_user('comparison_athlete', password='pass', role='athlete')
        peer = User.objects.create_user('comparison_peer', password='pass', role='athlete')
        GymMembership.objects.create(gym=gym, user=coach, role='coach')
        GymMembership.objects.create(gym=gym, user=athlete, role='athlete')
        GymMembership.objects.create(gym=gym, user=peer, role='athlete')
        group = TrainingGroup.objects.create(gym=gym, name='Silver')
        TrainingGroupCoach.objects.create(group=group, coach=coach)
        TrainingGroupAthlete.objects.create(group=group, athlete=athlete)
        TrainingGroupAthlete.objects.create(group=group, athlete=peer)
        session = DailyRoutineSession.objects.create(gym=gym, practice_date=date(2026, 9, 30))
        DailyRoutineAttempt.objects.create(session=session, athlete=athlete, event='vault', attempt_number=1, result='wow')
        DailyRoutineAttempt.objects.create(session=session, athlete=peer, event='vault', attempt_number=1, result='hit')
        attempts = list(DailyRoutineAttempt.objects.filter(session=session))

        rows = build_group_quick_comparison(coach, athlete, attempts, gym.pk)
        vault_routine = next(row for row in rows if row['event'] == 'Vault' and row['context'] == 'Routine')

        self.assertEqual(vault_routine['athlete_counts']['wow'], 1)
        self.assertEqual(vault_routine['group_average']['hit'], 0.5)
        self.assertEqual(vault_routine['group_athletes'], 2)
