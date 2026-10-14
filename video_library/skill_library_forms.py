from pathlib import Path
from django import forms
from .models import Video


class SkillExampleForm(forms.Form):
    title = forms.CharField(max_length=180, label='Example title')
    event = forms.ChoiceField(choices=Video.EVENT_CHOICES)
    skill_name = forms.CharField(max_length=150, label='Skill name',
                                help_text='Use the same skill name as the athlete attempts you want to compare.')
    camera_view = forms.ChoiceField(choices=Video.CAMERA_VIEW_CHOICES, initial='side',
                                   help_text='Side-view recordings support joint-angle comparisons. Other views can still be watched side by side.')
    notes = forms.CharField(required=False, label='Teaching notes', widget=forms.Textarea(attrs={'rows': 3}))
    video = forms.FileField(label='Skill video', help_text='MP4, MOV, M4V or WebM; up to 500 MB. The existing worker prepares it for playback.')
    analyze = forms.BooleanField(required=False, initial=True, label='Run free pose analysis after conversion')

    def __init__(self, *args, editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        if editing:
            self.fields.pop('video')
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field, forms.BooleanField) else 'form-select' if isinstance(field, forms.ChoiceField) else 'form-control'
        self.fields['skill_name'].widget.attrs['list'] = 'skill-example-names'
        if 'video' in self.fields:
            self.fields['video'].widget.attrs['accept'] = '.mp4,.mov,.m4v,.webm,video/mp4,video/quicktime,video/webm'

    def clean_skill_name(self):
        return ' '.join(self.cleaned_data['skill_name'].split())

    def clean_video(self):
        file = self.cleaned_data['video']
        if Path(file.name).suffix.lower() not in {'.mp4', '.mov', '.m4v', '.webm'}:
            raise forms.ValidationError('Choose an MP4, MOV, M4V or WebM video.')
        if file.size > 500 * 1024 * 1024:
            raise forms.ValidationError('The video exceeds the 500 MB limit.')
        content_type = getattr(file, 'content_type', '')
        if content_type and not (content_type.startswith('video/') or content_type == 'application/octet-stream'):
            raise forms.ValidationError('This file does not appear to be a video.')
        return file


class SkillApprovalForm(forms.Form):
    confirmed = forms.BooleanField(label='I have reviewed this video and approve it as a skill example for our gym.',
                                   widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
