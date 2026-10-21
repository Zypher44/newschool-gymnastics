from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from gyms.models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach
from routine_tracker.models import DailyRoutineAttempt, DailyRoutineSession
from .views import routine_comparison_rows


class RoutineComparisonTests(TestCase):
    def test_comparison_uses_only_same_assigned_group_and_splits_pressure(self):
        User = get_user_model()
        gym = Gym.objects.create(name='Report gym')
        coach = User.objects.create_user('report_coach', password='pass', role='coach')
        child = User.objects.create_user('report_child', password='pass', role='athlete')
        peer = User.objects.create_user('report_peer', password='pass', role='athlete')
        outside = User.objects.create_user('report_outside', password='pass', role='athlete')
        for user, role in ((coach, 'coach'), (child, 'athlete'), (peer, 'athlete'), (outside, 'athlete')):
            GymMembership.objects.create(gym=gym, user=user, role=role)
        group = TrainingGroup.objects.create(gym=gym, name='Silver')
        TrainingGroupCoach.objects.create(group=group, coach=coach)
        TrainingGroupAthlete.objects.create(group=group, athlete=child)
        TrainingGroupAthlete.objects.create(group=group, athlete=peer)

        session = DailyRoutineSession.objects.create(gym=gym, practice_date=date(2026, 9, 29))
        DailyRoutineAttempt.objects.create(session=session, athlete=child, event='vault', attempt_number=1, result='wow')
        DailyRoutineAttempt.objects.create(session=session, athlete=child, event='vault', attempt_number=1, result='hit', is_pressure=True)
        DailyRoutineAttempt.objects.create(session=session, athlete=peer, event='vault', attempt_number=1, result='hit')
        DailyRoutineAttempt.objects.create(session=session, athlete=peer, event='vault', attempt_number=2, result='missed')
        DailyRoutineAttempt.objects.create(session=session, athlete=outside, event='vault', attempt_number=1, result='missed')

        allowed = User.objects.filter(pk__in=(child.pk, peer.pk, outside.pk))
        rows = routine_comparison_rows(coach, child, allowed, date(2026, 9, 29), date(2026, 9, 29))
        regular = next(row for row in rows if row['event'] == 'Vault' and not row['is_pressure'])
        pressure = next(row for row in rows if row['event'] == 'Vault' and row['is_pressure'])

        self.assertEqual(regular['athlete_counts']['wow'], 1)
        self.assertEqual(regular['group_average']['hit'], 0.5)
        self.assertEqual(regular['group_athletes'], 2)
        self.assertEqual(pressure['athlete_counts']['hit'], 1)
        self.assertEqual(pressure['group_athletes'], 1)
