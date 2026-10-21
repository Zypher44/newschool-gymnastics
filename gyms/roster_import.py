"""Director roster planning and atomic application. Preview never writes accounts."""
import hashlib
import json
import re
from collections import Counter
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry, ADDITION
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from athletes.models import AthleteProfile
from coaches.models import CoachProfile
from parents_portal.models import ParentProfile, ParentAthleteLink
from .models import Gym, GymMembership, TrainingGroup, TrainingGroupAthlete, TrainingGroupCoach, RosterIdentity
from .roster_schema import ROLES

User=get_user_model()


def split_values(value):
    return [part.strip() for part in value.split(';') if part.strip()]


def roster_fingerprint(gym):
    ids=GymMembership.objects.filter(gym=gym).values_list('user_id',flat=True)
    snapshot={
        'members':list(GymMembership.objects.filter(gym=gym).order_by('pk').values('pk','user_id','role','is_active')),
        'users':list(User.objects.filter(pk__in=ids).order_by('pk').values('pk','username','first_name','last_name','email','phone','role','is_active','is_staff','is_superuser')),
        'profiles':list(AthleteProfile.objects.filter(user_id__in=ids).order_by('pk').values('user_id','date_of_birth','level')),
        'groups':list(TrainingGroup.objects.filter(gym=gym).order_by('pk').values('pk','name','is_active')),
        'group_athletes':list(TrainingGroupAthlete.objects.filter(group__gym=gym).order_by('pk').values('group_id','athlete_id','is_active')),
        'group_coaches':list(TrainingGroupCoach.objects.filter(group__gym=gym).order_by('pk').values('group_id','coach_id','role')),
        'links':list(ParentAthleteLink.objects.filter(parent_id__in=ids,athlete_id__in=ids).order_by('pk').values('pk','parent_id','athlete_id','relationship','approved')),
        'identities':list(RosterIdentity.objects.filter(gym=gym).order_by('pk').values('user_id','roster_id')),
        # Global names prevent an intervening account creation from changing the plan.
        'usernames':list(User.objects.order_by('pk').values_list('username',flat=True)),
        'memberships':list(GymMembership.objects.filter(user_id__in=ids).order_by('pk').values('user_id','gym_id','is_active')),
    }
    return hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest()


def plan_import(gym, rows, allow_updates=False):
    members={m.user_id:m for m in GymMembership.objects.filter(gym=gym).select_related('user')}
    identities={i.roster_id:i.user_id for i in RosterIdentity.objects.filter(gym=gym)}
    identity_by_user={user_id:key for key,user_id in identities.items()}
    names={}
    for user in User.objects.all(): names.setdefault(user.username.casefold(),[]).append(user)
    all_groups=list(TrainingGroup.objects.filter(gym=gym))
    group_names={g.name.casefold():g for g in all_groups}
    canonical_groups={g.name.casefold():g.name for g in all_groups}
    errors=[]; warnings=[]; people=[]; used_ids=set(); used_usernames=set(); used_users=set()
    def error(row,message): errors.append(f"{row['sheet']}, row {row['row']}: {message}")
    for source in rows:
        row=dict(source); rid=row.get('roster_id',''); role=ROLES.get(row['sheet'],row.get('role',''))
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',rid): error(row,'roster_id must be 1–64 letters, numbers, dots, dashes or underscores.');continue
        if rid.casefold().startswith('example'): error(row,'Replace example rows with your real roster.');continue
        if rid.casefold() in used_ids: error(row,'Duplicate roster_id in this workbook.');continue
        used_ids.add(rid.casefold())
        if role not in ('athlete','parent','coach','head_coach'): error(row,'Role must be coach or head_coach on the Coaches tab.');continue
        if not row.get('first_name') or not row.get('last_name'): error(row,'First name and last name are required.');continue
        if any(len(row.get(key,''))>limit for key,limit in [('first_name',150),('last_name',150),('email',254),('phone',30),('level',100),('relationship',50)]): error(row,'One of the name, email, phone, level or relationship fields is too long.');continue
        email=row.get('email','').strip().lower()
        if email:
            try: validate_email(email)
            except ValidationError: error(row,'Enter a valid email address.');continue
        row['email']=email
        dob=None
        if row.get('date_of_birth'):
            try:
                dob=date.fromisoformat(row['date_of_birth'])
                if not date(1900,1,1)<=dob<=timezone.localdate(): raise ValueError
            except ValueError: error(row,'Date of birth must be a real date in YYYY-MM-DD format, not in the future.');continue
        if role=='athlete' and dob is None: error(row,'Athletes need a date of birth.');continue
        user=None; rid_user=identities.get(rid)
        # IDs are case-sensitive; disallow near-identical variants.
        if any(key.casefold()==rid.casefold() and key!=rid for key in identities): error(row,'Use the exact exported spelling of roster_id.');continue
        if rid_user:
            user=members.get(rid_user).user if rid_user in members else None
            if user is None: error(row,'This roster ID no longer has a gym membership. Use Manage People.');continue
        explicit=row.get('username','')
        if explicit:
            try: User._meta.get_field('username').run_validators(explicit)
            except ValidationError: error(row,'Username contains unsupported characters or exceeds 150 characters.');continue
            matches=names.get(explicit.casefold(),[])
            if user and explicit!=user.username: error(row,'Username does not match this roster ID. Keep the exported username.');continue
            if not user and matches:
                if len(matches)!=1 or matches[0].pk not in members: error(row,'Username is unavailable. Use a unique username or export this gym’s existing roster.');continue
                user=matches[0]
        if user:
            member=members[user.pk]
            if user.role!=role or member.role!=role: error(row,'Role changes must be made in Manage People before importing.');continue
            if not user.is_active or not member.is_active: error(row,'This account or membership is inactive. Review it in Manage People.');continue
            if user.is_staff or user.is_superuser or user.role not in ('athlete','parent','coach','head_coach'): error(row,'Privileged accounts cannot be changed by roster imports.');continue
            if GymMembership.objects.filter(user=user,is_active=True).exclude(gym=gym).exists(): error(row,'Shared accounts must be managed individually; import cannot change them.');continue
            if user.pk in used_users: error(row,'The same account is listed more than once.');continue
            if user.pk in identity_by_user and identity_by_user[user.pk]!=rid: error(row,'Keep this person’s existing roster_id from the export.');continue
            used_users.add(user.pk)
            username=user.username
        else:
            username=explicit or f'g{gym.pk}_{rid}'.lower()
            try: User._meta.get_field('username').run_validators(username)
            except ValidationError: error(row,'Choose a shorter valid username.');continue
            if username.casefold() in names: error(row,'Generated username is unavailable. Enter a unique username.');continue
            # No guessing: require explicit reconciliation of likely existing people.
            candidates=User.objects.filter(pk__in=members,role=role,first_name__iexact=row['first_name'],last_name__iexact=row['last_name'])
            if role=='athlete': candidates=candidates.filter(athlete_profile__date_of_birth=dob)
            if candidates.exists() or (email and User.objects.filter(pk__in=members,role=role,email__iexact=email).exists()):
                error(row,'Possible existing person. Export the roster and use their username/roster_id, or resolve the duplicate in Manage People.');continue
        if username.casefold() in used_usernames: error(row,'Duplicate username in this import.');continue
        used_usernames.add(username.casefold())
        groups=split_values(row.get('groups',''))
        if len(groups)>20 or any(len(name)>150 for name in groups): error(row,'Use at most 20 group names, each up to 150 characters.');continue
        canonical=[]
        for name in groups:
            existing=group_names.get(name.casefold())
            if existing and not existing.is_active: error(row,f'Group {name} is inactive. Review it before importing.')
            canonical.append(canonical_groups.setdefault(name.casefold(),name))
        changes={}
        if user:
            for key in ['first_name','last_name','email','phone']:
                if row.get(key) and row[key]!=getattr(user,key): changes[key]={'before':getattr(user,key),'after':row[key]}
            if role=='athlete':
                profile=AthleteProfile.objects.filter(user=user).first()
                for key,value in [('date_of_birth',row.get('date_of_birth')),('level',row.get('level'))]:
                    old=getattr(profile,key,None) if profile else None
                    if value and value!=str(old or ''): changes[key]={'before':str(old or ''),'after':value}
        if user and changes and not allow_updates: error(row,'Existing details differ. Enable “Update existing details” to approve these field changes, or restore the exported values.')
        people.append({'sheet':row['sheet'],'row':row['row'],'roster_id':rid,'role':role,'username':username,
            'user_id':user.pk if user else None,'values':row,'groups':sorted(set(canonical)),
            'athlete_ids':split_values(row.get('athlete_ids','')),'changes':changes,'action':'Update' if user and changes else 'Keep' if user else 'Create'})
        if user is None and not email: warnings.append(f'{rid}: no email; an invitation cannot be emailed until an address is added.')
    by_id={person['roster_id']:person for person in people}
    for person in people:
        if person['role']!='parent':continue
        for aid in person['athlete_ids']:
            target=by_id.get(aid)
            target_user=identities.get(aid)
            if target:
                if target['role']!='athlete': errors.append(f"{person['roster_id']}: {aid} is not an athlete ID.")
            elif not target_user or target_user not in members or members[target_user].user.role!='athlete' or not members[target_user].is_active or not members[target_user].user.is_active:
                errors.append(f"{person['roster_id']}: athlete ID {aid} is not in this workbook or the gym’s saved roster.")
    # Workbook-internal possible duplicates must also be resolved before accounts exist.
    demographics=Counter((p['role'],p['values']['first_name'].casefold(),p['values']['last_name'].casefold(),p['values'].get('date_of_birth','')) for p in people if not p['user_id'])
    if any(count>1 for count in demographics.values()): errors.append('Possible duplicate people in this file. Review repeated names and dates of birth.')
    emails=Counter(p['values'].get('email') for p in people if p['values'].get('email'))
    if any(count>1 for count in emails.values()): warnings.append('Some people share an email address. Check that each account and family connection is intentional.')
    groups=sorted({name for p in people for name in p['groups'] if name.casefold() not in group_names})
    return {'people':people,'errors':errors[:200],'warnings':warnings[:100], 'new_groups':groups,
        'counts':dict(Counter(p['action'] for p in people)),'fingerprint':roster_fingerprint(gym),
        'family_links':sum(len(set(p['athlete_ids'])) for p in people),'group_assignments':sum(len(p['groups']) for p in people)}


def apply_import(batch):
    with transaction.atomic():
        Gym.objects.select_for_update().get(pk=batch.gym_id)
        batch=type(batch).objects.select_for_update().get(pk=batch.pk)
        from .tenant import single_active_gym_id
        if not batch.director.is_active or batch.director.role!='director' or single_active_gym_id(batch.director,['director'])!=batch.gym_id:
            raise ValidationError('Director access changed. This import cannot be applied.')
        if batch.status=='applied': return batch
        if batch.status!='preview' or timezone.now()-batch.created_at>timedelta(hours=2): raise ValidationError('This preview expired. Upload the file again.')
        fresh=plan_import(batch.gym,batch.rows,batch.allow_updates)
        if fresh['errors'] or fresh!=batch.preview: raise ValidationError('The roster or account availability changed since preview. Upload again to review the latest plan.')
        users={}; created=[]
        for person in fresh['people']:
            values=person['values']; role=person['role']
            if person['user_id']:
                user=User.objects.select_for_update().get(pk=person['user_id'])
            else:
                user=User(username=person['username'],role=role,first_name=values['first_name'],last_name=values['last_name'],email=values.get('email',''),phone=values.get('phone',''))
                user.set_unusable_password();user.save();created.append(user)
                GymMembership.objects.create(gym=batch.gym,user=user,role=role,is_active=True)
            if person['changes']:
                for key in ['first_name','last_name','email','phone']:
                    if key in person['changes']:setattr(user,key,values[key])
                user.save()
            if role=='athlete':
                profile,_=AthleteProfile.objects.get_or_create(user=user)
                if not person['user_id'] or batch.allow_updates:
                    if values.get('date_of_birth'):profile.date_of_birth=date.fromisoformat(values['date_of_birth'])
                    if values.get('level'):profile.level=values['level']
                    profile.save()
            elif role in ('coach','head_coach'):CoachProfile.objects.get_or_create(user=user)
            elif role=='parent':ParentProfile.objects.get_or_create(user=user)
            RosterIdentity.objects.get_or_create(gym=batch.gym,user=user,defaults={'roster_id':person['roster_id']})
            users[person['roster_id']]=user
            for name in person['groups']:
                group,_=TrainingGroup.objects.get_or_create(gym=batch.gym,name=name)
                if role=='athlete':TrainingGroupAthlete.objects.update_or_create(group=group,athlete=user,defaults={'is_active':True})
                else:TrainingGroupCoach.objects.get_or_create(group=group,coach=user,defaults={'role':role})
        for person in fresh['people']:
            if person['role']!='parent':continue
            for rid in set(person['athlete_ids']):
                athlete=users.get(rid)
                if athlete is None:athlete=RosterIdentity.objects.select_related('user').get(gym=batch.gym,roster_id=rid).user
                parent=users[person['roster_id']]
                link,created_link=ParentAthleteLink.objects.get_or_create(parent=parent,athlete=athlete,defaults={'approved':True,'relationship':person['values'].get('relationship','')})
                if not link.approved:link.approved=True;link.save(update_fields=['approved'])
        batch.created_users.add(*created)
        batch.status='applied';batch.applied_at=timezone.now();batch.save(update_fields=['status','applied_at'])
        LogEntry.objects.log_actions(user_id=batch.director_id,queryset=[batch.gym],action_flag=ADDITION,
            change_message=f'Confirmed roster import {batch.pk}: {len(fresh["people"])} people, {len(created)} new accounts.')
        return batch
