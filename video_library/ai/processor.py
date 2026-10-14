from django.db import transaction
from django.utils import timezone

from video_library.models import (
    Video,
    VideoAnalysis,
    VideoAnalysisMoment,
)

from .evidence_engine import EvidenceAnalysisEngine
from .cv_pipeline import (
    ComputerVisionPipeline,
)

class VideoAnalysisProcessor:
    """
    Coordinate the complete video-analysis pipeline.

    Views should request processing through this class rather
    than writing results directly into database models.
    """

    def __init__(
            self,
            engine=None,
            cv_pipeline=None,
    ):
        self.engine = (
                engine
                or EvidenceAnalysisEngine()
        )

        if self.engine.source == 'mock':
            raise ValueError('Demonstration engines cannot process production analyses.')

        self.cv_pipeline = (
                cv_pipeline
                or ComputerVisionPipeline()
        )

    def process(
        self,
        analysis: VideoAnalysis,
    ) -> VideoAnalysis:
        try:
            analysis.mark_started(
                step='Preparing video',
            )

            cv_results = (
                self.cv_pipeline.process(
                    analysis=analysis,
                )
            )

            result = self.engine.analyze(
                analysis=analysis,
            )

            result.raw_results[
                'computer_vision'
            ] = cv_results

            self._save_result(
                analysis=analysis,
                result=result,
            )

            return analysis

        except Exception as error:
            analysis.mark_failed(
                message='Analysis could not finish. Check the video and try again.',
            )

            analysis.video.ai_status = (
                Video.AI_FAILED
            )

            analysis.video.save(
                update_fields=[
                    'ai_status',
                    'updated_at',
                ],
            )

            raise

    @transaction.atomic
    def _save_result(
        self,
        analysis,
        result,
    ):
        if analysis.worker_token and not VideoAnalysis.objects.select_for_update().filter(
                pk=analysis.pk, worker_token=analysis.worker_token, lease_expires_at__gt=timezone.now()).exists():
            raise RuntimeError('Analysis worker lease expired before results were saved.')

        analysis.analysis_source = (
            self.engine.source
        )

        analysis.analysis_version = (
            self.engine.version
        )

        analysis.detected_skill = (
            result.detected_skill
        )

        analysis.skill_confidence = (
            result.skill_confidence
        )

        analysis.summary = result.summary
        analysis.strengths = result.strengths
        analysis.improvements = result.improvements
        analysis.measurements = result.measurements
        analysis.raw_results = result.raw_results

        analysis.save(
            update_fields=[
                'analysis_source',
                'analysis_version',
                'detected_skill',
                'skill_confidence',
                'summary',
                'strengths',
                'improvements',
                'measurements',
                'raw_results',
                'updated_at',
            ],
        )

        analysis.moments.filter(
            label__in=[
                'Start',
                'Key body position',
                'Alignment review',
                'Finish',
            ],
            frame_image='',
        ).delete()

        VideoAnalysisMoment.objects.bulk_create([
            VideoAnalysisMoment(
                analysis=analysis,
                timestamp_seconds=(
                    moment.timestamp_seconds
                ),
                moment_type=moment.moment_type,
                label=moment.label,
                description=moment.description,
                severity=moment.severity,
                confidence=moment.confidence,
                measurements=moment.measurements,
                display_order=moment.display_order,
            )
            for moment in result.moments
        ])

        analysis.mark_completed()

        video = analysis.video

        video.ai_status = Video.AI_COMPLETED
        video.ai_summary = result.summary

        video.ai_results = {
            'analysis_id': analysis.id,
            'detected_skill': (
                result.detected_skill
            ),
            'confidence': (float(result.skill_confidence) if result.skill_confidence is not None else None),
            'analysis_source': (
                self.engine.source
            ),
            'analysis_version': (
                self.engine.version
            ),
            'mock_analysis': self.engine.source == 'mock',
            'selected_skill': analysis.requested_skill,
            'coach_review_required': True,
        }

        video.save(
            update_fields=[
                'ai_status',
                'ai_summary',
                'ai_results',
                'updated_at',
            ],
        )