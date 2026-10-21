import csv
import io
import zipfile
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_GET
from django.utils import timezone
from .views import get_director_gym
from .models import RosterImport, RosterIdentity, GymMembership
from .roster_files import parse_uploads, workbook_bytes
from .roster_import import plan_import, apply_import
from .roster_schema import SCHEMAS


class RosterUploadForm(forms.Form):
    workbook = forms.FileField(required=False, label='Excel workbook (.xlsx)')
    athletes_csv = forms.FileField(required=False, label='Athletes CSV')
    parents_csv = forms.FileField(required=False, label='Parents & Guardians CSV')
    coaches_csv = forms.FileField(required=False, label='Coaches CSV')
    allow_updates = forms.BooleanField(required=False, label='Update existing details shown in the preview')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for name in ('workbook','athletes_csv','parents_csv','coaches_csv'):
            self.fields[name].widget.attrs.update({'class':'form-control','accept':'.xlsx' if name=='workbook' else '.csv'})

    def clean(self):
        data=super().clean()
        csvs=any(data.get(key) for key in ('athletes_csv','parents_csv','coaches_csv'))
        if bool(data.get('workbook'))==bool(csvs): raise ValidationError('Choose one Excel workbook OR one or more roster CSV files.')
        return data


def director_gym(request):
    gym=get_director_gym(request.user)
    if gym is None or not request.user.is_active: raise Http404
    return gym


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def roster_import(request):
    gym=director_gym(request)
    form=RosterUploadForm(request.POST if request.method=='POST' else None, request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            data=form.cleaned_data
            rows=parse_uploads(data.get('workbook'), {'Athletes':data.get('athletes_csv'),
                'Parents & Guardians':data.get('parents_csv'),'Coaches':data.get('coaches_csv')})
            preview=plan_import(gym,rows,data['allow_updates'])
            batch=RosterImport.objects.create(gym=gym,director=request.user,rows=rows,preview=preview,allow_updates=data['allow_updates'])
            return redirect('roster_import_preview',batch_id=batch.pk)
        except ValidationError as error:form.add_error(None,error)
    batches=RosterImport.objects.filter(gym=gym,director=request.user).order_by('-created_at')[:10]
    return render(request,'gyms/roster_import.html',{'gym':gym,'form':form,'batches':batches})


@login_required
@never_cache
@require_http_methods(['GET','POST'])
def roster_preview(request,batch_id):
    gym=director_gym(request)
    batch=get_object_or_404(RosterImport,pk=batch_id,gym=gym,director=request.user)
    if request.method=='POST':
        action=request.POST.get('action')
        if action=='apply':
            if request.POST.get('confirm')!='yes':
                messages.error(request,'Confirm the reviewed accounts and family access before importing.')
            else:
                try:
                    batch=apply_import(batch)
                    messages.success(request,'Roster imported. No invitations have been sent.')
                except (ValidationError,IntegrityError) as error:
                    messages.error(request,' '.join(error.messages) if isinstance(error,ValidationError) else 'An account changed during import. Nothing was saved. Upload again for a fresh preview.')
        elif action=='setup_link' and batch.status=='applied':
            from .roster_invitations import eligible_setup_user, password_setup_path
            raw=request.POST.get('user_id','')
            user=batch.created_users.filter(pk=raw).first() if raw.isdigit() else None
            if user and eligible_setup_user(batch,user):
                request.session['roster_setup_link']={'batch':str(batch.pk),'username':user.username,
                    'url':request.build_absolute_uri(password_setup_path(user))}
            else:messages.error(request,'This account is not eligible for a setup link.')
        elif action=='invitations' and batch.status=='applied':
            from .roster_invitations import send_invitations
            result=send_invitations(batch)
            if result['sent']:messages.success(request,f"{result['sent']} invitation(s) submitted. Send again to continue; sent invitations are skipped.")
            if result['error']:messages.error(request,result['error'])
        else:messages.error(request,'Choose a valid action.')
        return redirect('roster_import_preview',batch_id=batch.pk)
    from practice_focus.email_provider import email_configuration
    setup_link=request.session.pop('roster_setup_link',None)
    if setup_link and setup_link.get('batch')!=str(batch.pk):setup_link=None
    return render(request,'gyms/roster_preview.html',{'gym':gym,'batch':batch,'preview':batch.preview,'setup_link':setup_link,
        'expired':timezone.now()-batch.created_at>timedelta(hours=2),
        'email_available':not bool(email_configuration()),
        'new_accounts':batch.created_users.order_by('role','first_name','username') if batch.status=='applied' else [],
        'invitations':batch.invitations.select_related('user')})


def export_tables(gym):
    members=list(GymMembership.objects.filter(gym=gym,is_active=True,user__is_active=True,
        role__in=['athlete','parent','coach','head_coach'],user__is_staff=False,user__is_superuser=False).select_related('user').order_by('user_id'))
    members=[m for m in members if m.role==m.user.role]
    identities={i.user_id:i.roster_id for i in RosterIdentity.objects.filter(gym=gym)}
    used=set(identities.values()); keys={}
    for member in members:
        key=identities.get(member.user_id)
        if key is None:
            key=f'NS-{member.user_id}'
            while key in used:key+='-X'
        used.add(key);keys[member.user_id]=key
    tables={sheet:[] for sheet in SCHEMAS}
    from parents_portal.models import ParentAthleteLink
    from .models import TrainingGroupAthlete, TrainingGroupCoach
    for member in members:
        user=member.user
        base=[keys[user.pk],user.username,user.first_name,user.last_name,user.email,user.phone]
        if member.role=='athlete':
            profile=getattr(user,'athlete_profile',None)
            groups=TrainingGroupAthlete.objects.filter(athlete=user,is_active=True,group__gym=gym,group__is_active=True).values_list('group__name',flat=True)
            tables['Athletes'].append(base+[str(profile.date_of_birth) if profile and profile.date_of_birth else '',profile.level if profile else '', '; '.join(sorted(groups))])
        elif member.role=='parent':
            links=ParentAthleteLink.objects.filter(parent=user,approved=True,athlete_id__in=keys).order_by('athlete_id')
            # One parent can have different relationships to different children. Reuse saved relationships on import.
            relationships=set(links.values_list('relationship',flat=True))
            tables['Parents & Guardians'].append(base+['; '.join(keys[link.athlete_id] for link in links),next(iter(relationships)) if len(relationships)==1 else ''])
        else:
            groups=TrainingGroupCoach.objects.filter(coach=user,group__gym=gym,group__is_active=True).values_list('group__name',flat=True)
            tables['Coaches'].append(base+[member.role,'; '.join(sorted(groups))])
    return tables


def csv_bytes(headers,rows):
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(headers)
    for row in rows:
        # Force spreadsheet software to read user-controlled values as literal text.
        writer.writerow(["'"+str(value) if str(value).lstrip().startswith(('=','+','-','@','\t','\r')) else value for value in row])
    return ('\ufeff'+out.getvalue()).encode('utf-8')


@login_required
@never_cache
@require_GET
def roster_download(request):
    gym=director_gym(request)
    kind=request.GET.get('kind','template')
    if kind=='template':content=workbook_bytes();name='newschool-roster-template.xlsx';mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif kind=='export':content=workbook_bytes(export_tables(gym));name='newschool-gym-roster.xlsx';mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif kind=='csv':
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
            for sheet,rows in export_tables(gym).items():archive.writestr(sheet.replace(' & ','-').lower()+'.csv',csv_bytes(SCHEMAS[sheet],rows))
        content=out.getvalue();name='newschool-gym-roster-csv.zip';mime='application/zip'
    else:raise Http404
    response=HttpResponse(content,content_type=mime)
    response['Content-Disposition']=f'attachment; filename="{name}"'
    response['X-Content-Type-Options']='nosniff'
    return response
