from django.db import transaction

from .models import AthleteTestingResult


@transaction.atomic
def update_session_rankings(session):
    results = list(
        AthleteTestingResult.objects.filter(
            session=session,
            status='verified'
        ).select_related(
            'athlete'
        ).order_by(
            '-total_score',
            'athlete__username'
        )
    )

    current_rank = 0
    athletes_seen = 0
    previous_score = None

    for result in results:
        athletes_seen += 1

        if previous_score is None or result.total_score != previous_score:
            current_rank = athletes_seen

        result.rank = current_rank
        result.save(update_fields=['rank'])

        previous_score = result.total_score

    AthleteTestingResult.objects.filter(
        session=session
    ).exclude(
        status='verified'
    ).update(rank=None)

    return results


@transaction.atomic
def recalculate_session_scores(session):
    results = AthleteTestingResult.objects.filter(
        session=session
    )

    for result in results:
        result.calculate_total_score()

    update_session_rankings(session)