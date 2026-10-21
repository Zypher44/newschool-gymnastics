from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from parents_portal.models import ParentAthleteLink
from .models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach, RosterImport
from .setup_checklist import completion_checklist


class SetupChecklistTests(TestCase):
    def setUp(self):
        self.gym = Gym.objects.create(name='Checklist Gym')
        self.other_gym = Gym.objects.create(name='Other Checklist Gym')
        self.director = self.person('check-director','director')
        self.child = self.person('check-child','athlete')
        self.parent = self.person('check-parent','parent')
        self.coach = self.person('check-coach','coach')
        self.client.force_login(self.director)

    def person(self,name,role,gym=None,password=None):
        user=get_user_model().objects.create_user(username=name,role=role,password=password)
        GymMembership.objects.create(gym=gym or self.gym,user=user,role=role)
        return user

    def counts(self):
        return {check['key']:check['count'] for check in completion_checklist(self.gym)['checks']}

    def test_live_checks_clear_after_real_password_parent_and_group_fixes(self):
        self.assertEqual(self.counts(),{'passwords':3,'parents':1,'groups':2})
        for user in [self.child,self.parent,self.coach]:
            user.set_password('A-valid-password-213!');user.save()
        ParentAthleteLink.objects.create(parent=self.parent,athlete=self.child,approved=True)
        group=TrainingGroup.objects.create(gym=self.gym,name='Team A')
        TrainingGroupAthlete.objects.create(group=group,athlete=self.child)
        TrainingGroupCoach.objects.create(group=group,coach=self.coach)
        checklist=completion_checklist(self.gym)
        self.assertTrue(checklist['complete'])
        self.assertEqual(self.counts(),{'passwords':0,'parents':0,'groups':0})
        self.assertContains(self.client.get(reverse('setup_checklist')),'All three setup checks are complete')
        self.assertEqual(checklist['people_count'],3)

    def test_pending_inactive_and_foreign_parents_do_not_complete_connections(self):
        link=ParentAthleteLink.objects.create(parent=self.parent,athlete=self.child,approved=False)
        self.assertEqual(self.counts()['parents'],1)
        link.approved=True;link.save()
        self.assertEqual(self.counts()['parents'],0)
        GymMembership.objects.filter(user=self.parent,gym=self.gym).update(is_active=False)
        self.assertEqual(self.counts()['parents'],1)
        GymMembership.objects.create(user=self.parent,gym=self.other_gym,role='parent')
        self.assertEqual(self.counts()['parents'],1)

    def test_inactive_groups_and_memberships_do_not_complete_group_check(self):
        group=TrainingGroup.objects.create(gym=self.gym,name='Inactive team',is_active=False)
        TrainingGroupAthlete.objects.create(group=group,athlete=self.child)
        TrainingGroupCoach.objects.create(group=group,coach=self.coach)
        self.assertEqual(self.counts()['groups'],2)
        group.is_active=True;group.save()
        self.assertEqual(self.counts()['groups'],0)
        TrainingGroupAthlete.objects.filter(group=group).update(is_active=False)
        self.assertEqual(self.counts()['groups'],1)

    def test_only_active_normal_matching_members_are_counted(self):
        self.person('foreign-child','athlete',self.other_gym)
        inactive=self.person('inactive-child','athlete')
        GymMembership.objects.filter(user=inactive).update(is_active=False)
        staff=self.person('staff-child','athlete');staff.is_staff=True;staff.save()
        disabled=self.person('disabled-child','athlete');disabled.is_active=False;disabled.save()
        mismatch=self.person('mismatch-child','athlete');GymMembership.objects.filter(user=mismatch).update(role='parent')
        data=completion_checklist(self.gym)
        self.assertEqual(data['people_count'],3)
        self.assertEqual({r['username'] for r in data['buckets']['passwords']},{self.child.username,self.parent.username,self.coach.username})
        self.assertNotIn(self.parent.pk,{r['id'] for r in data['buckets']['groups']})

    def test_empty_gym_has_no_false_completion(self):
        GymMembership.objects.filter(gym=self.gym).exclude(user=self.director).delete()
        data=completion_checklist(self.gym)
        self.assertFalse(data['complete'])
        self.assertEqual(data['people_count'],0)
        response=self.client.get(reverse('setup_checklist'))
        self.assertContains(response,'Your roster is empty')
        self.assertNotContains(response,'All three setup checks are complete')

    def test_director_scope_and_read_only_actions(self):
        foreign=self.person('foreign-name','athlete',self.other_gym)
        response=self.client.get(reverse('setup_checklist'),{'gym':self.other_gym.pk})
        self.assertContains(response,self.child.username)
        self.assertNotContains(response,foreign.username)
        self.assertNotIn('password',response.context['page'].object_list[0])
        self.assertEqual(self.client.post(reverse('setup_checklist')).status_code,405)
        for user in [self.coach,self.parent,self.child]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('setup_checklist')).status_code,404)
        self.client.force_login(self.director)
        GymMembership.objects.filter(user=self.director).update(is_active=False)
        self.assertEqual(self.client.get(reverse('setup_checklist')).status_code,404)

    def test_shared_account_has_no_unsupported_reset_action(self):
        GymMembership.objects.create(user=self.child,gym=self.other_gym,role='athlete')
        row=next(row for row in completion_checklist(self.gym)['buckets']['passwords'] if row['id']==self.child.pk)
        self.assertTrue(row['shared']);self.assertEqual(row['action_url'],'')
        response=self.client.get(reverse('setup_checklist'),{'check':'passwords'})
        self.assertContains(response,'Shared with another gym')

    def test_import_and_applied_preview_include_live_summary_without_mutation(self):
        response=self.client.get(reverse('roster_import'))
        self.assertContains(response,'Setup completion checklist')
        self.assertEqual(response.context['setup_checklist']['people_count'],3)
        batch=RosterImport.objects.create(gym=self.gym,director=self.director,status='applied',preview={'people':[]})
        before={model.__name__:model.objects.count() for model in [GymMembership,TrainingGroup,ParentAthleteLink]}
        response=self.client.get(reverse('roster_import_preview',args=[batch.pk]))
        self.assertContains(response,'Setup completion checklist')
        self.assertEqual(before,{model.__name__:model.objects.count() for model in [GymMembership,TrainingGroup,ParentAthleteLink]})
        self.assertEqual(self.client.get(reverse('setup_checklist'),{'check':'bogus','page':'invalid'}).status_code,200)
