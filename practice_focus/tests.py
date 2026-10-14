from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, Client, override_settings
from django.template import Context, Template
from django.urls import reverse
from gyms.models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete
from parents_portal.models import ParentAthleteLink
from .models import EventSkillPlan, EVENTS
from .templatetags.practice_focus_tags import current_skills, visible_plans


# Keep testing the original event-text form separately from the newer personal
# planner, whose POST format and athlete redirect intentionally differ.
from django.urls import include, path
from DjangoProject.urls import urlpatterns as application_urls
from .urls import urlpatterns as focus_urls
from . import views as legacy_views

legacy_focus_urls = [
    path('', legacy_views.planner, name='planner'),
    *[entry for entry in focus_urls if entry.name != 'planner'],
]
urlpatterns = [
    path('practice-planner/current-skills/', include((legacy_focus_urls, 'practice_focus'))),
    *[entry for entry in application_urls if getattr(entry, 'app_name', None) != 'practice_focus'],
]


@override_settings(ROOT_URLCONF='practice_focus.tests')
class CurrentSkillsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.gym = Gym.objects.create(name='Gym A')
        cls.other_gym = Gym.objects.create(name='Gym B')
        cls.coach = User.objects.create_user(username='coach', role='coach')
        cls.head = User.objects.create_user(username='head', role='head_coach')
        cls.athlete = User.objects.create_user(username='athlete', role='athlete')
        cls.other = User.objects.create_user(username='other', role='athlete')
        cls.parent = User.objects.create_user(username='parent', role='parent')
        cls.stranger = User.objects.create_user(username='stranger', role='parent')
        cls.unaffiliated = User.objects.create_user(username='unaffiliated', role='coach')
        for user in [cls.coach, cls.head, cls.athlete, cls.parent, cls.stranger]:
            GymMembership.objects.create(gym=cls.gym, user=user, role=user.role)
        GymMembership.objects.create(gym=cls.other_gym, user=cls.other, role='athlete')
        cls.group = TrainingGroup.objects.create(gym=cls.gym, name='Level 3')
        TrainingGroupAthlete.objects.create(group=cls.group, athlete=cls.athlete)
        cls.link = ParentAthleteLink.objects.create(parent=cls.parent, athlete=cls.athlete, approved=True)

    def setUp(self):
        self.client.force_login(self.coach)
        self.url = reverse('practice_focus:planner')

    def data(self, athlete=None):
        data = {'athlete': (athlete or self.athlete).pk, 'group': ''}
        for code, _ in EVENTS:
            plan = EventSkillPlan.objects.filter(gym=self.gym, athlete=athlete or self.athlete, event=code).first()
            data.update({f'{code}-skills_text': f'{code} skill', f'{code}-training_cues': 'Stay tight',
                         f'{code}-version': plan.updated_at.isoformat() if plan else ''})
        return data

    def request(self, user):
        request = RequestFactory().get('/')
        request.user = user
        return request

    def plan(self, athlete=None, gym=None):
        return EventSkillPlan.objects.create(gym=gym or self.gym, athlete=athlete or self.athlete,
            event='beam', skills_text='Back walkover\nCartwheel', training_cues='Straight arms')

    def test_page_shows_four_events_and_existing_groups(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Level 3')
        for _, label in EVENTS:
            self.assertContains(response, label)
        self.assertNotContains(response, '>other<')

    def test_save_all_events_and_reload(self):
        response = self.client.post(self.url, self.data(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current skills saved')
        self.assertEqual(EventSkillPlan.objects.count(), 4)
        self.assertContains(response, 'beam skill')
        self.assertEqual(EventSkillPlan.objects.get(event='beam').updated_by, self.coach)

    def test_normalizes_duplicate_skills(self):
        data = self.data(); data['beam-skills_text'] = ' Cartwheel \r\n\r\ncartwheel\nBack walkover'
        self.client.post(self.url, data)
        self.assertEqual(EventSkillPlan.objects.get(event='beam').skill_names, ['Cartwheel', 'Back walkover'])

    def test_invalid_event_prevents_partial_save(self):
        data = self.data(); data['beam-skills_text'] = 'x' * 151
        self.assertEqual(self.client.post(self.url, data).status_code, 200)
        self.assertEqual(EventSkillPlan.objects.count(), 0)

    def test_clear_event_without_deleting_other_events(self):
        self.client.post(self.url, self.data())
        data = self.data(); data['beam-skills_text']=''; data['beam-training_cues']=''
        self.client.post(self.url, data)
        self.assertEqual(EventSkillPlan.objects.get(event='beam').skill_names, [])
        self.assertEqual(EventSkillPlan.objects.get(event='vault').skill_names, ['vault skill'])

    def test_stale_update_preserves_latest_save(self):
        stale = self.data()
        self.client.post(self.url, self.data())
        response = self.client.post(self.url, stale)
        self.assertContains(response, 'Another coach updated')
        self.assertEqual(EventSkillPlan.objects.count(), 4)

    def test_existing_stale_update_is_atomic(self):
        self.client.post(self.url, self.data())
        stale = self.data()
        latest = self.data(); latest['beam-skills_text']='New skill'
        self.client.post(self.url, latest)
        stale['vault-skills_text']='Overwrite attempt'
        self.client.post(self.url, stale)
        self.assertEqual(EventSkillPlan.objects.get(event='beam').skills_text, 'New skill')
        self.assertEqual(EventSkillPlan.objects.get(event='vault').skills_text, 'vault skill')

    def test_other_gym_athlete_get_and_post_blocked(self):
        self.assertEqual(self.client.get(self.url, {'athlete': self.other.pk}).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.data(self.other)).status_code, 404)
        self.assertEqual(EventSkillPlan.objects.count(), 0)

    def test_foreign_group_blocked(self):
        group=TrainingGroup.objects.create(gym=self.other_gym, name='Foreign')
        self.assertEqual(self.client.get(self.url, {'group':group.pk}).status_code,404)

    def test_group_filter_uses_director_group_assignments(self):
        response=self.client.get(self.url, {'group':self.group.pk})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['selected_athlete'],self.athlete)

    def test_noncoach_roles_cannot_manage(self):
        for user in [self.athlete,self.parent,self.stranger]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code,403)
            self.assertEqual(self.client.post(self.url,self.data()).status_code,403)

    def test_no_gym_and_ambiguous_gym_blocked(self):
        self.client.force_login(self.unaffiliated)
        self.assertEqual(self.client.get(self.url).status_code,403)
        GymMembership.objects.create(gym=self.other_gym,user=self.coach,role='coach')
        self.client.force_login(self.coach)
        self.assertEqual(self.client.get(self.url).status_code,403)

    def test_head_coach_can_save(self):
        self.client.force_login(self.head)
        self.assertEqual(self.client.post(self.url,self.data()).status_code,302)

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code,302)

    def test_csrf_required_for_save(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.coach)
        self.assertEqual(client.post(self.url,self.data()).status_code,403)

    def test_read_only_athlete_and_approved_parent(self):
        self.plan()
        for user in [self.athlete,self.parent]:
            context=Context({'request':self.request(user)})
            focus=current_skills(context,self.athlete,'beam')
            self.assertEqual(focus['plans'][0].skill_names,['Back walkover','Cartwheel'])
            self.assertFalse(focus['can_edit'])

    def test_unlinked_parent_and_other_athlete_cannot_read(self):
        self.plan()
        for user in [self.stranger,self.other]:
            focus=current_skills(Context({'request':self.request(user)}),self.athlete,'beam')
            self.assertEqual(focus['plans'],[])

    def test_revoked_parent_link_cannot_read(self):
        self.plan(); self.link.approved=False; self.link.save()
        self.assertEqual(current_skills(Context({'request':self.request(self.parent)}),self.athlete,'beam')['plans'],[])

    def test_inactive_athlete_membership_cannot_read_or_manage(self):
        self.plan()
        GymMembership.objects.filter(user=self.athlete).update(is_active=False)
        self.assertEqual(self.client.get(self.url,{'athlete':self.athlete.pk}).status_code,404)
        self.assertEqual(current_skills(Context({'request':self.request(self.parent)}),self.athlete,'beam')['plans'],[])

    def test_other_gym_skills_do_not_leak(self):
        self.plan(self.other,self.other_gym)
        self.assertEqual(current_skills(Context({'request':self.request(self.coach)}),self.other,'beam')['plans'],[])

    def test_template_escapes_skill_names_and_notes(self):
        plan=self.plan();plan.skills_text='<script>alert(1)</script>';plan.save()
        html=Template('{% load practice_focus_tags %}{% current_skills athlete "beam" %}').render(Context({'request':self.request(self.athlete),'athlete':self.athlete}))
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)

    def test_plan_cache_only_queries_skills_once(self):
        self.plan()
        request=self.request(self.coach)
        visible_plans(request)
        with self.assertNumQueries(0):
            visible_plans(request)

    def test_malformed_selection_returns_404(self):
        self.assertEqual(self.client.get(self.url,{'athlete':'bad'}).status_code,404)

    def test_blank_new_events_do_not_create_empty_rows(self):
        data=self.data()
        for code,_ in EVENTS:
            data[f'{code}-skills_text']='';data[f'{code}-training_cues']=''
        self.client.post(self.url,data)
        self.assertEqual(EventSkillPlan.objects.count(),0)
