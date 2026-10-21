# Start Practice and Getting Started

## Install locally

Save `apply_v3_start_practice_onboarding.py` beside `manage.py`, then run these
commands in the PyCharm terminal from the project folder:

```powershell
python apply_v3_start_practice_onboarding.py
python run_v3_local.py migrate
python run_v3_local.py check
python run_v3_local.py runserver
```

Use the existing `run_v3_local.py` launcher so this project continues to use
your configured PostgreSQL database. If you already configured the same database
for `manage.py`, its corresponding migrate/check/runserver commands are also valid.
Stop any running development server before installing, then restart and hard
refresh the browser. PyCharm should pick up the new `practice_hub` folder.

No new Python packages, email credentials, or manual URL edits are needed.
This patch requires the existing individual practice planner, both trackers,
and the practice progress/review upgrade. It does not require the report email
provider to be configured. It preserves existing scores, plans, parent links,
report privacy settings, and report navigation.

The installer checks all file changes before writing and keeps backups of the
three integration files. Re-running it is safe when those files are unchanged.
If the current base template has a different structure, installation stops before
changing files and explains which anchor could not be found.

## Start Practice

- Coach and head coach navigation: **Home → Start Practice**.
- Direct URL: `/practice/start/`.
- Choose a training group and its first event, then start practice.
- Group buttons keep all authorized athlete names accessible. Select one child
  to see their individual skills, repetition targets, routines, and pressure sets.
- Start Practice uses the saved individual plan for today. If no plan is saved,
  it shows current active skill assignments without inventing attempt targets.
- A saved plan can contain skills that are not active in the tracker. The screen
  flags this and links back to the planner; use the planner's existing action to
  set current skills. Opening or starting practice never silently changes a plan.
- Open Skill Tracker or Routine Tracker with the group, child, and event already
  selected. The tracker includes **Back to [group] practice** and an option to
  show all events. Existing autosave, Undo, review, and celebrations are reused.
- The rotation timer uses a saved server timestamp and continues across reloads
  and tracker visits. It is a quiet reminder; coaches choose when to move on.
- **Mark unrecorded present** creates attendance only where no record exists.
  Existing absences, late/excused statuses, and notes are preserved. Open the
  selected child's attendance section for an intentional correction.
- **Finish practice** keeps the results and provides review/report links.
  **Resume practice** reopens it if needed. Finishing does not approve scores,
  publish reports, send emails, or clear outstanding tracker saves.
- Practice totals are for the athlete/event/date, including entries awaiting
  review. They are not additional scores or a separate scoring session.
- Each coach has one resumable workspace per group/day. Different coaches can
  use their own workspace. Head coaches see the gym's groups; regular coaches
  see only groups and athletes authorized by their existing assignments.

## Guided onboarding

- All supported roles have **Getting Started** in navigation.
- Direct URL: `/practice/getting-started/`.
- A welcome banner offers the appropriate guide until it is completed or saved
  for later. It does not force users away from their normal dashboard.
- Directors: gym details, people, group assignments, coaching workflow, families.
- Coaches/head coaches: roster, individual plans, demo scoring, review/sharing,
  and first practice.
- Athletes: their plan, a safe scoring demo, progress, and practice basics.
- Parents: approved child connection, published progress, shared feedback,
  messages/notifications, and dashboard.
- The guide reuses existing information and opens the real management pages in
  a new tab. It does not duplicate gym accounts or bulk-create people.
- Review each lesson, tick the box, and save/continue. Progress is stored for
  that person, gym, and role and resumes on another device.
- **Save for later** hides the welcome banner. The navigation link stays.
- Completed guides can be revisited or restarted without deleting gym data.
- Completing a guide acknowledges its lessons; it does not automatically approve
  membership/parent links or certify that every setup task is finished.
- Pending or ambiguous membership shows a connection message without revealing
  athlete or gym information. Parent access still requires gym approval.
- Demo Wow/Hit/Attempt buttons are local examples; they do not save scores.

## Render deployment later

Commit the new `practice_hub` folder and migration plus the three integration
files (`DjangoProject/settings.py`, `DjangoProject/urls.py`, `templates/base.html`).
Run your usual migrations and `collectstatic --noinput` during deployment.
This feature needs no additional Render environment variables. Email setup
remains separate and can wait until the new version is deployed.

## Validation included in development

Role/gym permissions, assigned coach rosters, mixed-level plans, tracker links,
attendance preservation and stale edits, idempotent starts/finishes, resuming,
rotation timers, onboarding state and stale tabs, pending parent links, and CSRF
are covered by isolated tests. No production database or user emails are used.
