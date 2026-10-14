import json
from datetime import timedelta
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.utils import timezone
from gyms.models import Gym, GymMembership
from practice_focus.models import EventSkillPlan
from .models import Skill, Assignment, SkillResult


class SkillTrackerTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='Gym A')
        self.other = Gym.objects.create(name='Gym B')
        self.coach = self.user('coach', 'head_coach', self.gym)
        self.athlete = self.user('athlete', 'athlete', self.gym)
        self.peer = self.user('peer', 'athlete', self.gym)
        self.outsider = self.user('outsider', 'athlete', self.other)
        self.plan = EventSkillPlan.objects.create(gym=self.gym, athlete=self.athlete,
            event='beam', skills_text='Back handspring\nSplit leap', training_cues='Stay tall', updated_by=self.coach)
        self.assignment = Assignment.objects.filter(athlete=self.athlete).first()
        self.client.force_login(self.coach)

    def user(self, name, role, gym):
        u = get_user_model().objects.create_user(username=name, role=role)
        GymMembership.objects.create(user=u, gym=gym, role=role)
        return u

    def payload(self, athlete=None, entries=None):
        return {'athlete': (athlete or self.athlete).pk, 'date': str(timezone.localdate()),
            'entries': entries or [{'assignment': self.assignment.pk, 'result': 'wow', 'token': str(uuid4())}]}

    def save(self, payload):
        return self.client.post('/skill-tracker/save/', json.dumps(payload), content_type='application/json')

    def assignment_post(self, ids):
        plans = {p.event:p for p in EventSkillPlan.objects.filter(athlete=self.athlete)}
        data = {'action':'assign','athlete':self.athlete.pk,'skills':ids}
        for event in ['vault','bars','beam','floor']:
            data['version_'+event] = plans[event].updated_at.isoformat() if event in plans else ''
        return data

    def test_coach_and_athlete_pages_render(self):
        self.assertContains(self.client.get('/skill-tracker/'), 'Skill Tracker')
        self.assertContains(self.client.get('/skill-tracker/manage/'), 'Save athlete skills')
        self.client.force_login(self.athlete)
        response=self.client.get('/skill-tracker/')
        self.assertContains(response, 'Back handspring')
        self.assertNotContains(response, 'Manage skills')

    def test_planner_signal_deduplicates_names(self):
        self.plan.skills_text='Back handspring\n  BACK   handspring \nNew skill'
        self.plan.save()
        self.assertEqual(Assignment.objects.filter(athlete=self.athlete,is_active=True).count(),2)
        self.assertEqual(Skill.objects.filter(gym=self.gym,event='beam',key='back handspring').count(),1)

    def test_assignment_updates_planner_preserves_cues(self):
        skill=Skill.objects.create(gym=self.gym,event='floor',name='Round-off',key='round-off')
        response=self.client.post('/skill-tracker/manage/',self.assignment_post([skill.pk]))
        self.assertEqual(response.status_code,302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.skills_text,'')
        self.assertEqual(self.plan.training_cues,'Stay tall')
        self.assertEqual(EventSkillPlan.objects.get(athlete=self.athlete,event='floor').skills_text,'Round-off')
        self.assertTrue(Assignment.objects.get(skill=skill,athlete=self.athlete).is_active)

    def test_stale_assignment_save_rejected(self):
        data=self.assignment_post([])
        self.plan.skills_text='New skill';self.plan.save()
        self.assertContains(self.client.post('/skill-tracker/manage/',data),'changed while you were editing')
        self.plan.refresh_from_db();self.assertEqual(self.plan.skills_text,'New skill')

    def test_catalogue_reuse_case_insensitive(self):
        for names in ['Round-off\nROUND-OFF', 'Round-off']:
            self.assertEqual(self.client.post('/skill-tracker/manage/',{'action':'catalogue','event':'floor','names':names}).status_code,302)
        self.assertEqual(Skill.objects.filter(event='floor',gym=self.gym).count(),1)

    def test_bad_catalogue_input(self):
        response=self.client.post('/skill-tracker/manage/',{'action':'catalogue','event':'unknown','names':'X'})
        self.assertContains(response,'Choose an event.')
        self.assertEqual(Skill.objects.count(),2)

    def test_all_results_saved_and_counted(self):
        payload=self.payload(entries=[{'assignment':self.assignment.pk,'result':result,'token':str(uuid4())} for result in ['wow','hit','missed']])
        self.assertEqual(self.save(payload).status_code,200)
        self.assertEqual(SkillResult.objects.count(),3)
        self.assertContains(self.client.get('/skill-tracker/?athlete='+str(self.athlete.pk)), 'data-wow="1"')
        self.assertContains(self.client.get('/skill-tracker/?athlete='+str(self.athlete.pk)), 'Attempt')

    def test_retry_does_not_duplicate(self):
        payload=self.payload()
        self.assertEqual(self.save(payload).status_code,200)
        self.assertEqual(self.save(payload).status_code,200)
        self.assertEqual(SkillResult.objects.count(),1)

    def test_token_reuse_different_payload_rejected(self):
        payload=self.payload();self.save(payload)
        payload['entries'][0]['result']='hit'
        self.assertEqual(self.save(payload).status_code,400)
        self.assertEqual(SkillResult.objects.count(),1)

    def test_invalid_batch_is_atomic(self):
        payload=self.payload()
        payload['entries'].append({'assignment':999999,'result':'hit','token':str(uuid4())})
        self.assertEqual(self.save(payload).status_code,400)
        self.assertEqual(SkillResult.objects.count(),0)

    def test_inactive_assignment_rejected_history_retained(self):
        self.save(self.payload())
        self.plan.skills_text='';self.plan.save()
        self.assertEqual(self.save(self.payload()).status_code,400)
        self.assertEqual(SkillResult.objects.count(),1)

    def test_coach_other_gym_denied(self):
        self.assertEqual(self.client.get('/skill-tracker/?athlete='+str(self.outsider.pk)).status_code,404)
        self.assertEqual(self.save(self.payload(athlete=self.outsider)).status_code,404)

    def test_foreign_skill_cannot_be_assigned(self):
        skill=Skill.objects.create(gym=self.other,event='beam',name='X',key='x')
        response=self.client.post('/skill-tracker/manage/',self.assignment_post([skill.pk]))
        self.assertContains(response,'Choose skills from your gym')
        self.plan.refresh_from_db();self.assertIn('Back handspring',self.plan.skills_text)

    def test_athlete_can_only_log_self(self):
        self.client.force_login(self.athlete)
        self.assertEqual(self.save(self.payload()).status_code,200)
        self.assertEqual(self.save(self.payload(athlete=self.peer)).status_code,403)
        self.assertEqual(self.client.get('/skill-tracker/manage/').status_code,403)

    def test_athlete_query_does_not_expose_peer(self):
        EventSkillPlan.objects.create(gym=self.gym,athlete=self.peer,event='floor',skills_text='Secret peer skill')
        self.client.force_login(self.athlete)
        self.assertNotContains(self.client.get('/skill-tracker/?athlete='+str(self.peer.pk)), 'Secret peer skill')

    def test_inactive_membership_denied(self):
        GymMembership.objects.filter(user=self.coach).update(is_active=False)
        self.assertEqual(self.client.get('/skill-tracker/').status_code,403)

    def test_parent_denied(self):
        parent=self.user('parent','parent',self.gym);self.client.force_login(parent)
        self.assertEqual(self.client.get('/skill-tracker/').status_code,403)

    def test_dates_and_bad_json_rejected(self):
        self.client.force_login(self.athlete)
        payload=self.payload();payload['date']=str(timezone.localdate()-timedelta(days=1))
        self.assertEqual(self.save(payload).status_code,400)
        for value in [[],{}, {'entries':'bad'}]:
            self.assertEqual(self.save(value).status_code,400)
        self.assertEqual(SkillResult.objects.count(),0)

    def test_csrf_enforced(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.athlete)
        self.assertEqual(client.post('/skill-tracker/save/',json.dumps(self.payload()),content_type='application/json').status_code,403)

    def test_get_cannot_save(self):
        self.assertEqual(self.client.get('/skill-tracker/save/').status_code,405)
