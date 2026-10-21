"""PostgreSQL-backed jobs. Requests enqueue; separate workers do the work."""
from datetime import timedelta
import uuid
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Video, VideoAnalysis

ACTIVE_STATUSES = ['queued', 'preparing', 'processing', 'generating_results']
MAX_ATTEMPTS = 3


@transaction.atomic
def enqueue_analysis(video, user=None, *, requested_skill=None):
    # Lock the owning video so two requests cannot create duplicate active jobs.
    video = Video.objects.select_for_update().get(pk=video.pk)
    existing = video.analyses.filter(status__in=ACTIVE_STATUSES).order_by('-created_at').first()
    if existing:
        return existing, False
    if video.status in [Video.STATUS_FAILED, Video.STATUS_ARCHIVED]:
        raise ValueError('The video must finish conversion before analysis can be requested.')
    analysis = VideoAnalysis.objects.create(
        video=video, requested_by=user, requested_skill=requested_skill if requested_skill is not None else video.skill_name,
        analysis_source=VideoAnalysis.SOURCE_POSE, analysis_version='pose-evidence-1.0.0',
        raw_results={'camera_view': video.camera_view},
        current_step='Waiting for video conversion' if video.status != Video.STATUS_READY else 'Waiting for analysis worker',
    )
    Video.objects.filter(pk=video.pk).update(ai_status=Video.AI_QUEUED, updated_at=timezone.now())
    return analysis, True


@transaction.atomic
def claim_analysis(*, timeout_seconds=600):
    analysis = (VideoAnalysis.objects.select_for_update(skip_locked=True)
                .filter(status=VideoAnalysis.STATUS_QUEUED, video__status=Video.STATUS_READY)
                .filter(Q(retry_after__isnull=True) | Q(retry_after__lte=timezone.now())))
    analysis = analysis.order_by('created_at').first()
    if analysis is None:
        return None
    analysis.worker_token = uuid.uuid4()
    analysis.lease_expires_at = timezone.now() + timedelta(seconds=timeout_seconds + 90)
    analysis.processing_attempts += 1
    analysis.status = VideoAnalysis.STATUS_PREPARING
    analysis.current_step = 'Preparing analysis'
    analysis.retry_after = None
    analysis.save(update_fields=['worker_token', 'lease_expires_at', 'processing_attempts', 'status', 'current_step', 'retry_after', 'updated_at'])
    Video.objects.filter(pk=analysis.video_id).update(ai_status=Video.AI_PROCESSING, updated_at=timezone.now())
    return analysis


@transaction.atomic
def finish_attempt(analysis_id, token, *, error=None, source_missing=False):
    owner = VideoAnalysis.objects.filter(pk=analysis_id).values_list('video_id', flat=True).first()
    if owner is None:
        return
    Video.objects.select_for_update().get(pk=owner)
    analysis = VideoAnalysis.objects.select_for_update().filter(pk=analysis_id, worker_token=token).first()
    if analysis is None:
        return
    if analysis.status != VideoAnalysis.STATUS_COMPLETED:
        # Detailed runtime errors stay in worker logs; user-visible failures are safe.
        analysis.error_message = (
            'The uploaded video file is unavailable in the worker storage. Restore the file or check storage settings, then request analysis again.'
            if source_missing else 'Analysis could not finish. Check the video and try again.'
        )
        newer_job = VideoAnalysis.objects.filter(video_id=owner, status__in=ACTIVE_STATUSES).exclude(pk=analysis_id).exists()
        if not source_missing and analysis.processing_attempts < MAX_ATTEMPTS and not newer_job:
            analysis.status = VideoAnalysis.STATUS_QUEUED
            analysis.retry_after = timezone.now() + timedelta(seconds=30 * analysis.processing_attempts)
            analysis.current_step = 'Waiting to retry analysis'
            video_status = Video.AI_QUEUED
        else:
            analysis.status = VideoAnalysis.STATUS_FAILED
            analysis.current_step = 'Video file unavailable' if source_missing else 'Analysis failed; request a new analysis to retry'
            analysis.completed_at = timezone.now()
            video_status = Video.AI_FAILED
        analysis.progress_percentage = 0
        if not newer_job:
            Video.objects.filter(pk=analysis.video_id).update(ai_status=video_status, updated_at=timezone.now())
    analysis.worker_token = None
    analysis.lease_expires_at = None
    analysis.save()


def recover_expired_jobs():
    jobs = VideoAnalysis.objects.filter(worker_token__isnull=False, lease_expires_at__lt=timezone.now()).values_list('pk', 'worker_token')
    for pk, token in list(jobs):
        finish_attempt(pk, token, error='Worker lease expired')
    # A failed conversion or archive must not leave a permanent queued analysis.
    waiting = VideoAnalysis.objects.filter(status='queued', video__status__in=['failed', 'archived'])
    unavailable = list(waiting.values_list('video_id', flat=True))
    waiting.update(status='failed', current_step='Video unavailable for analysis',
                   error_message='The video must finish conversion before analysis.', completed_at=timezone.now(), updated_at=timezone.now())
    Video.objects.filter(pk__in=unavailable, ai_status='queued', status__in=['failed', 'archived']).update(
        ai_status=Video.AI_FAILED, updated_at=timezone.now())
