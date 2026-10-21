# NewSchoolGymnastics V3 — Skill Tracker

A separate Skill Tracker for coaches, head coaches and athletes. Your current Practice Planner and Routine Tracker remain in place.

## Install in PyCharm on Windows

Stop the development server. Extract all ZIP contents directly into the folder containing `manage.py` and `run_v3_local.py`:

`C:\Users\Owner\PycharmProjects\newschool-gymnastics-v2-test`

You should see `skill_tracker` and `apply_v3_skill_tracker.py` alongside `manage.py`. Do not nest them inside another package folder.

Run in the PyCharm terminal with your virtual environment active:

```powershell
python apply_v3_skill_tracker.py
python run_v3_local.py migrate
python run_v3_local.py check
python run_v3_local.py runserver
```

Use your local V3 database password when the launcher prompts. Migration imports existing current skills automatically. The installer backs up settings, project URLs and the base template before editing them. It is safe to run the installer again. It does not replace your existing planner or routine templates.

Open http://127.0.0.1:8000/skill-tracker/ or use the new sidebar link. Coach setup is at http://127.0.0.1:8000/skill-tracker/manage/.

This update requires the working `practice_focus` current-skills planner already installed in your V3 project.

## Coach workflow

1. Open **Manage skills → Add to skill list**. Choose an event and enter skill names, one per line.
2. Select an athlete and click **Load athlete**.
3. Check skills under Vault, Bars, Beam and Floor; click **Save athlete skills**.
4. The same assignments appear in the Practice Planner and its existing Routine Tracker integration. Existing training cues are preserved.

Skills are reusable across athletes in the same gym. Removing an assignment keeps saved history. Editing an athlete’s current skill list in the existing planner synchronizes tracker assignments as well. Case and extra spaces do not create duplicate catalogue entries.

## Athlete workflow

1. Choose a currently assigned skill within an event.
2. Tap **Wow**, **Hit**, or **Attempt** for each completed attempt.
3. Review **This practice**, use **Undo** for mistakes, then click **Save practice**.

Today’s per-skill totals include pending results. Results are not stored until Save practice succeeds. Unsaved results trigger a navigation warning; do not close the page until saved. Failed saves preserve pending results for retry. Retry tokens prevent duplicate entries if a response is lost. Athletes can record only their own results for today; coaches can select active athletes in their own gym. This page does not alter routine-level results or routine consistency calculations.

## Layout

Four event cards, familiar Wow/Hit/Attempt colors, a single save bar and recent results. Mobile uses one card per row, 46-pixel controls, wrapped history rows and 16-pixel input text. Styles are scoped to this feature.

## Validation

Validated with Django 5.2.7 against the recovered accounts and gyms models in an isolated SQLite test project:

- 20 Django tests: permissions, same-gym assignments, planner synchronization, stale editing, atomic saves, dates, CSRF, history and duplicate retries.
- Installer preflight, backup and repeat-install tests.
- Migration from a pre-existing planner list, including duplicate names and repeat import.
- JavaScript DOM checks for selection, totals, Undo, unsaved warnings and failed-save retry.

Your complete live project, PostgreSQL database, sidebar styling and real mobile browser were not available in this workspace. Check the installed page on your phone before deployment. Deploying later will also require migrations and your normal static-file collection.

To run the included app tests with your usual test database configuration:

```powershell
python manage.py test skill_tracker
```

The tests are included in `skill_tracker/tests.py`; the local launcher currently supports only migrate, check and runserver, so use your normal test settings for the test command.
