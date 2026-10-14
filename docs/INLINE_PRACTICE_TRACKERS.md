# Skill and routine tracking on the practice page

Select an athlete in Start Practice or Practice Planner: both trackers appear on that page.
Choose an event and, when needed, a skill, then tap Wow, Hit or Attempt. A single assigned
skill is selected automatically. Routine and pressure-set targets stay separate.
Saved targets and progress update as results save. Undo last is beside each autosave status.
Recent results remain available for Undo. The shared durable outbox preserves retries and
keeps a result attached to its original child when another child is selected.
Athletes also get both trackers on My Practice Plan. Their entries await coach review.
Start Practice retains attendance and all group/child timer controls. Tracker taps retain
Wow/Hit confetti, sounds and personal milestones. Coach plan editing is in Edit practice plan.
Past/future plans remain viewable; this practice-page scoring interface is for today.
Practice finished disables new taps until the coach resumes it.
Each widget shows only the selected child's assigned skills and saved targets.
Results use the existing database records, review queue, progress reports and weekly summaries.
Opening the practice page does not create routine sessions; the first routine result does.
Result snapshots have timestamps so late responses cannot replace more recent saved totals.

## Install
Install the previous practice-refinements patch first. Stop the development server.
Save this updater beside manage.py and run:
python apply_v3_inline_practice.py
python run_v3_local.py check
python run_v3_local.py runserver
No additional migration is required by this update. Hard-refresh with Ctrl+F5.
The installer backs up changed files, supports --check and is safe to run again.
Unexpected customized files are preserved and cause preflight to stop before any edits.
Email configuration and existing standalone tracker pages stay available.
