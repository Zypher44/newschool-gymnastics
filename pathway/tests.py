from django.test import TestCase

from .models import (
    PathwayEvent,
    PathwayLevel,
    PathwayRequirement,
)


class USAGOptionalPathwaySeedTests(TestCase):
    def test_levels_six_through_ten_are_seeded_separately(self):
        levels = PathwayLevel.objects.filter(
            program=PathwayLevel.PROGRAM_USAG_OPTIONAL,
        ).order_by('order')

        self.assertEqual(
            list(levels.values_list('order', flat=True)),
            [6, 7, 8, 9, 10],
        )
        self.assertEqual(
            PathwayLevel.objects.filter(program=PathwayLevel.PROGRAM_HP).count(),
            0,
        )

        self.assertEqual(
            PathwayEvent.objects.filter(
                code__in=['vault', 'bars', 'beam', 'floor'],
            ).count(),
            4,
        )

    def test_required_and_optional_rows_have_expected_scope(self):
        optional_levels = PathwayLevel.objects.filter(
            program=PathwayLevel.PROGRAM_USAG_OPTIONAL,
        )
        requirements = PathwayRequirement.objects.filter(
            level__in=optional_levels,
            is_active=True,
        )

        self.assertEqual(requirements.count(), 110)
        self.assertEqual(requirements.filter(is_required=True).count(), 95)
        self.assertEqual(requirements.filter(is_required=False).count(), 15)
        self.assertTrue(
            requirements.filter(
                title='Coach verification of selected vault',
                level__order__gte=8,
            ).exists()
        )
        self.assertTrue(
            requirements.filter(
                title='Value-part coverage',
                level__order=10,
            ).exists()
        )

    def test_optional_levels_do_not_claim_age_ranges(self):
        self.assertFalse(
            PathwayLevel.objects.filter(
                program=PathwayLevel.PROGRAM_USAG_OPTIONAL,
            ).exclude(
                minimum_age__isnull=True,
                maximum_age__isnull=True,
            ).exists()
        )
