"""Stop an image build which does not contain the updated, tested application."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    'practice_focus/models.py': 'AthleteJournalEntry',
    'practice_focus/urls.py': 'journal_history',
    'practice_focus/journal_views.py': 'journal_history',
    'practice_focus/migrations/0010_athletejournalentry.py': 'AthleteJournalEntry',
    'practice_focus/passport_badge_views.py': 'badge_editor',
    'practice_focus/personal_views.py': 'planner',
    'practice_hub/onboarding.py': 'lessons',
    'practice_hub/views.py': 'start_practice',
    'skill_tracker/urls.py': 'tracker',
    'video_library/migrations/0014_video_moment_notes.py': 'Migration',
    'video_library/moment_feedback_views.py': 'change_moment',
    'video_library/progress_views.py': 'def timeline(',
    'video_library/management/commands/process_video_jobs.py': 'process_video_queue',
    'DjangoProject/urls.py': 'practice_hub.urls',
    'DjangoProject/settings.py': 'practice_hub',
}


def check(root=ROOT):
    problems = []
    for name, marker in REQUIRED.items():
        path = root / name
        if not path.is_file():
            problems.append('Missing updated source: ' + name)
        elif marker not in path.read_text(encoding='utf-8-sig'):
            problems.append('Updated feature not registered: ' + name)
    model = root / 'video_library/ai/models/pose_landmarker_full.task'
    if not model.is_file() or model.stat().st_size < 1_000_000:
        problems.append('The MediaPipe pose model is missing or incomplete.')
    return problems


if __name__ == '__main__':
    problems = check()
    if problems:
        print('Test deployment stopped: push the latest complete PyCharm project first.', file=sys.stderr)
        for problem in problems:
            print(problem, file=sys.stderr)
        raise SystemExit(1)
    print('Updated V2 practice, journals, badges, and video source are present.')
