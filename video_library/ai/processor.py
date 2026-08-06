from django.db import transaction

from video_library.models import (
    Video,
    VideoAnalysis,
    VideoAnalysisMoment,
)

from .mock_engine import MockAnalysisEngine


class VideoAnalysisProcessor:
    """
    Coordinate the complete video-analysis pipeline.

    Views should request processing through this class rather
    than writing results directly into database models.
    """

    def __init__(
        self,
        engine=None,
    ):
        self.engine = (
            engine
            or MockAnalysisEngine()
        )

    def process(
        self,
        analysis: VideoAnalysis,
    ) -> VideoAnalysis:
        try:
            analysis.mark_started(
                step='Preparing video',
            )

            analysis.update_progress(
                percentage=25,
                step='Extracting video frames',
                status=(
                    VideoAnalysis.STATUS_PROCESSING
                ),
            )

            analysis.update_progress(
                percentage=55,
                step='Detecting athlete positions',
                status=(
                    VideoAnalysis.STATUS_PROCESSING
                ),
            )

            analysis.update_progress(
                percentage=80,
                step='Generating coaching observations',
                status=(
                    VideoAnalysis
                    .STATUS_GENERATING_RESULTS
                ),
            )

            result = self.engine.analyze(
                analysis=analysis,
            )

            self._save_result(
                analysis=analysis,
                result=result,
            )

            return analysis

        except Exception as error:
            analysis.mark_failed(
                message=error,
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

        analysis.moments.all().delete()

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
            'confidence': float(
                result.skill_confidence
            ),
            'analysis_source': (
                self.engine.source
            ),
            'analysis_version': (
                self.engine.version
            ),
            'mock_analysis': True,
        }

        video.save(
            update_fields=[
                'ai_status',
                'ai_summary',
                'ai_results',
                'updated_at',
            ],
        )