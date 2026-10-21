import csv
import io
import zipfile
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from athletes.models import AthleteProfile
from parents_portal.models import ParentAthleteLink
from .models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach, RosterImport, RosterIdentity
from .roster_schema import SCHEMAS
from .roster_files import parse_uploads, workbook_bytes
from .roster_import import plan_import, apply_import
from .roster_views import export_tables, csv_bytes


class RosterImportTests(TestCase):
    def setUp(self):
        self.gym=Gym.objects.create(name='Import Gym')
        self.other_gym=Gym.objects.create(name='Other Gym')
        self.director=self.person('director','director')
        self.other=self.person('foreign-director','director',self.other_gym)
        self.client.force_login(self.director)

    def person(self,name,role,gym=None,**extra):
        user=get_user_model().objects.create_user(username=name,role=role,**extra)
        GymMembership.objects.create(user=user,gym=gym or self.gym,role=role)
        return user

    def tables(self):
        return {'Athletes':[['A001','','Alex','Taylor','','+15551234','2015-04-12','Level 2','Team A']],
            'Parents & Guardians':[['P001','','Sam','Taylor','sam@example.com','','A001','Guardian']],
            'Coaches':[['C001','','Jo','Lee','jo@example.com','','head_coach','Team A']]}

    def rows(self,tables=None):
        upload=SimpleUploadedFile('roster.xlsx',workbook_bytes(tables or self.tables()))
        return parse_uploads(upload)

    def batch(self,rows=None,updates=False):
        rows=self.rows() if rows is None else rows
        plan=plan_import(self.gym,rows,updates)
        return RosterImport.objects.create(gym=self.gym,director=self.director,rows=rows,preview=plan,allow_updates=updates)

    def test_preview_is_readonly_and_apply_connects_roles_groups_and_profiles(self):
        before=get_user_model().objects.count()
        batch=self.batch()
        self.assertFalse(batch.preview['errors'],batch.preview['errors'])
        self.assertEqual(get_user_model().objects.count(),before)
        self.assertFalse(TrainingGroup.objects.exists())
        apply_import(batch)
        self.assertEqual(get_user_model().objects.count(),before+3)
        child=RosterIdentity.objects.get(gym=self.gym,roster_id='A001').user
        parent=RosterIdentity.objects.get(gym=self.gym,roster_id='P001').user
        coach=RosterIdentity.objects.get(gym=self.gym,roster_id='C001').user
        self.assertEqual(coach.role,'head_coach')
        self.assertEqual(str(AthleteProfile.objects.get(user=child).date_of_birth),'2015-04-12')
        self.assertTrue(ParentAthleteLink.objects.get(parent=parent,athlete=child).approved)
        self.assertTrue(TrainingGroupAthlete.objects.filter(athlete=child,group__name='Team A').exists())
        self.assertTrue(TrainingGroupCoach.objects.filter(coach=coach,role='head_coach').exists())
        self.assertFalse(child.has_usable_password())
        self.assertFalse(batch.invitations.exists())
        apply_import(batch);self.assertEqual(get_user_model().objects.count(),before+3)

    def test_repeat_upload_and_export_roundtrip_do_not_duplicate_or_remove(self):
        batch=self.batch();apply_import(batch)
        before=get_user_model().objects.count()
        again=self.batch();self.assertFalse(again.preview['errors']);apply_import(again)
        self.assertEqual(get_user_model().objects.count(),before)
        exported=export_tables(self.gym)
        roundtrip=self.batch(self.rows(exported));self.assertFalse(roundtrip.preview['errors'],roundtrip.preview['errors']);apply_import(roundtrip)
        self.assertEqual(get_user_model().objects.count(),before)
        self.assertEqual(ParentAthleteLink.objects.count(),1)
        self.assertEqual(TrainingGroupAthlete.objects.count(),1)

    def test_explicit_updates_preserve_password_and_blank_cells(self):
        apply_import(self.batch())
        user=RosterIdentity.objects.get(roster_id='A001').user
        user.set_password('Existing-password-123!');user.save()
        password=user.password
        rows=self.rows();rows[0]['first_name']='Alexandra';rows[0]['phone']=''
        denied=self.batch(rows);self.assertTrue(denied.preview['errors'])
        with self.assertRaises(ValidationError):apply_import(denied)
        allowed=self.batch(rows,True);self.assertFalse(allowed.preview['errors']);apply_import(allowed)
        user.refresh_from_db();self.assertEqual(user.first_name,'Alexandra');self.assertEqual(user.phone,'+15551234');self.assertEqual(user.password,password)

    def test_duplicates_bad_links_and_foreign_username_are_errors(self):
        self.person('taken','athlete',self.other_gym)
        rows=self.rows();rows[0]['username']='taken';rows[1]['athlete_ids']='FOREIGN-ID'
        plan=plan_import(self.gym,rows)
        self.assertTrue(any('unavailable' in error for error in plan['errors']))
        self.assertTrue(any('FOREIGN-ID' in error for error in plan['errors']))
        rows=self.rows();rows[1]['roster_id']='A001'
        self.assertTrue(plan_import(self.gym,rows)['errors'])
        self.assertEqual(get_user_model().objects.count(),3)

    def test_shared_or_privileged_existing_accounts_cannot_be_changed(self):
        user=self.person('existing','athlete',first_name='Alex',last_name='Taylor')
        AthleteProfile.objects.create(user=user,date_of_birth='2015-04-12')
        rows=self.rows();rows[0]['username']=user.username
        GymMembership.objects.create(user=user,gym=self.other_gym,role='athlete')
        self.assertTrue(plan_import(self.gym,rows)['errors'])
        GymMembership.objects.filter(user=user,gym=self.other_gym).delete()
        user.is_staff=True;user.save()
        self.assertTrue(plan_import(self.gym,rows)['errors'])

    def test_stale_or_expired_preview_rejected_and_database_error_rolls_back_all(self):
        batch=self.batch()
        self.person('new-since-preview','coach')
        with self.assertRaises(ValidationError):apply_import(batch)
        fresh=self.batch()
        with patch('gyms.roster_import.TrainingGroup.objects.get_or_create',side_effect=IntegrityError('simulated conflict')):
            with self.assertRaises(IntegrityError):apply_import(fresh)
        self.assertFalse(RosterIdentity.objects.exists());self.assertFalse(ParentAthleteLink.objects.exists())
        self.assertFalse(get_user_model().objects.filter(username__startswith='g').exists())
        RosterImport.objects.filter(pk=fresh.pk).update(created_at=timezone.now()-timedelta(hours=3))
        fresh.refresh_from_db()
        with self.assertRaises(ValidationError):apply_import(fresh)

    def test_csv_google_sheets_input_and_formula_safe_roundtrip(self):
        files={sheet:SimpleUploadedFile('tab.csv',csv_bytes(SCHEMAS[sheet],rows)) for sheet,rows in self.tables().items()}
        rows=parse_uploads(csv_files=files)
        self.assertEqual(rows[0]['phone'],'+15551234')
        self.assertFalse(plan_import(self.gym,rows)['errors'])
        safe=csv_bytes(['name'],[['=HYPERLINK("bad")']]).decode('utf-8-sig')
        self.assertIn("'=HYPERLINK",safe)

    def test_malformed_headers_formulas_and_oversized_files_rejected(self):
        with self.assertRaises(ValidationError):parse_uploads(SimpleUploadedFile('bad.xlsx',b'bad'))
        with self.assertRaises(ValidationError):parse_uploads(csv_files={'Athletes':SimpleUploadedFile('a.csv',b'wrong\nvalue')})
        content=workbook_bytes(self.tables());out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(content)) as source,zipfile.ZipFile(out,'w') as dest:
            for item in source.infolist():
                data=source.read(item.filename)
                if item.filename=='xl/worksheets/sheet1.xml':
                    from xml.etree import ElementTree as ET
                    from .roster_files import NS
                    root=ET.fromstring(data)
                    cell=root.find(f'.//{{{NS}}}sheetData/{{{NS}}}row/{{{NS}}}c')
                    ET.SubElement(cell,f'{{{NS}}}f').text='1+1'
                    data=ET.tostring(root)
                dest.writestr(item.filename,data)
        with self.assertRaises(ValidationError):parse_uploads(SimpleUploadedFile('formula.xlsx',out.getvalue()))

    def test_preview_ownership_confirm_checkbox_and_csrf(self):
        response=self.client.post(reverse('roster_import'),{'workbook':SimpleUploadedFile('roster.xlsx',workbook_bytes(self.tables()))})
        self.assertEqual(response.status_code,302)
        batch=RosterImport.objects.get()
        url=reverse('roster_import_preview',args=[batch.pk])
        self.assertContains(self.client.get(url),'A001')
        self.client.post(url,{'action':'apply'});batch.refresh_from_db();self.assertEqual(batch.status,'preview')
        client=Client(enforce_csrf_checks=True);client.force_login(self.director)
        self.assertEqual(client.post(url,{'action':'apply','confirm':'yes'}).status_code,403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code,404)
        child=self.person('not-director','athlete');self.client.force_login(child)
        self.assertEqual(self.client.get(reverse('roster_import')).status_code,404)
        self.assertEqual(self.client.get(reverse('roster_download')).status_code,404)

    def test_export_only_active_own_gym_people_and_no_passwords(self):
        apply_import(self.batch())
        self.person('foreign-child','athlete',self.other_gym)
        response=self.client.get(reverse('roster_download'),{'kind':'export'})
        self.assertEqual(response.status_code,200)
        rows=parse_uploads(SimpleUploadedFile('export.xlsx',response.content))
        self.assertEqual(len(rows),3)
        self.assertFalse(any('password' in key for row in rows for key in row))
        self.assertFalse(any(row.get('username')=='foreign-child' for row in rows))

    @override_settings(REPORT_EMAIL_API_KEY='fake',REPORT_EMAIL_FROM='gym@example.com',REPORT_EMAIL_APP_URL='https://example.com')
    @patch('gyms.roster_invitations.submit_email',return_value='provider-id')
    def test_invitations_separate_idempotent_and_password_setup_works(self,send):
        from .roster_invitations import send_invitations
        batch=self.batch();batch=apply_import(batch)
        send.assert_not_called()
        result=send_invitations(batch);self.assertEqual(result['sent'],2)
        send_invitations(batch);self.assertEqual(send.call_count,2)
        parent=RosterIdentity.objects.get(roster_id='P001').user
        path=reverse('roster_password_setup',kwargs={'uidb64':urlsafe_base64_encode(force_bytes(parent.pk)), 'token':default_token_generator.make_token(parent)})
        self.client.logout()
        response=self.client.get(path,follow=True);self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['validlink'])
        response=self.client.post(response.request['PATH_INFO'],{'new_password1':'New-strong-password-121!','new_password2':'New-strong-password-121!'},follow=True)
        parent.refresh_from_db();self.assertTrue(parent.check_password('New-strong-password-121!'))
        self.assertFalse(self.client.get(path,follow=True).context['validlink'])

    def test_existing_roster_without_import_ids_roundtrips_without_new_accounts(self):
        child=self.person('existing-child','athlete',first_name='Robin',last_name='Jones')
        AthleteProfile.objects.create(user=child,date_of_birth='2014-01-02')
        parent=self.person('existing-parent','parent',first_name='Pat',last_name='Jones')
        ParentAthleteLink.objects.create(parent=parent,athlete=child,approved=True,relationship='Parent')
        before=get_user_model().objects.count()
        batch=self.batch(self.rows(export_tables(self.gym)))
        self.assertFalse(batch.preview['errors'],batch.preview['errors'])
        apply_import(batch)
        self.assertEqual(get_user_model().objects.count(),before)
        self.assertEqual(RosterIdentity.objects.filter(gym=self.gym).count(),2)

    def test_multiple_children_and_guardians_and_omissions_keep_existing_links(self):
        tables=self.tables()
        tables['Athletes'].append(['A002','','Casey','Taylor','','','2016-02-03','','Team B'])
        tables['Parents & Guardians'][0][6]='A001; A002'
        tables['Parents & Guardians'].append(['P002','','Lee','Taylor','','','A001','Guardian'])
        batch=self.batch(self.rows(tables));self.assertFalse(batch.preview['errors']);apply_import(batch)
        self.assertEqual(ParentAthleteLink.objects.count(),3)
        tables['Parents & Guardians'][0][6]='A001'
        tables['Athletes'][0][-1]=''
        apply_import(self.batch(self.rows(tables)))
        self.assertEqual(ParentAthleteLink.objects.count(),3)
        self.assertEqual(TrainingGroupAthlete.objects.count(),2)

    def test_setup_link_only_after_explicit_post_and_owned_new_account(self):
        batch=apply_import(self.batch())
        child=RosterIdentity.objects.get(roster_id='A001').user
        url=reverse('roster_import_preview',args=[batch.pk])
        response=self.client.get(url)
        self.assertNotContains(response,'aria-label="Password setup link"')
        response=self.client.post(url,{'action':'setup_link','user_id':child.pk},follow=True)
        self.assertContains(response,'aria-label="Password setup link"')
        foreign=self.person('foreign-new','athlete',self.other_gym)
        response=self.client.post(url,{'action':'setup_link','user_id':foreign.pk},follow=True)
        self.assertNotContains(response,'aria-label="Password setup link"')

    @override_settings(REPORT_EMAIL_API_KEY='',REPORT_EMAIL_FROM='')
    @patch('gyms.roster_invitations.submit_email')
    def test_unconfigured_email_does_not_send_or_change_import(self,send):
        from .roster_invitations import send_invitations
        batch=apply_import(self.batch())
        result=send_invitations(batch)
        self.assertEqual(result['sent'],0);self.assertTrue(result['error'])
        send.assert_not_called();self.assertFalse(batch.invitations.exists())

    def test_coach_role_change_is_rejected_and_director_revocation_stops_confirmation(self):
        apply_import(self.batch())
        rows=self.rows();rows[2]['role']='coach'
        self.assertTrue(plan_import(self.gym,rows,True)['errors'])
        fresh=self.batch()
        GymMembership.objects.filter(user=self.director,gym=self.gym).update(is_active=False)
        with self.assertRaises(ValidationError):apply_import(fresh)
