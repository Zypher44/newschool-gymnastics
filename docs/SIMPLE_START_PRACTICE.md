# Simpler Start Practice

Install this update after the original Start Practice/onboarding installer:

```powershell
python apply_v3_simple_start_practice.py
python run_v3_local.py check
python run_v3_local.py runserver
```

Stop the running server first and save the installer beside manage.py. Restart
and hard-refresh the browser after installation. There are no database changes,
new migrations, or extra Python packages in this update.

## During practice

1. Tap the group. If you have one available group, it is already open.
2. **Everyone present** marks unrecorded athletes present in one click. Existing
   late, absent, and excused records and notes are preserved. Attendance
   corrections remain available in Practice tools.
3. The quiet rotation timer is visible at the top. It starts when you mark
   attendance, start the timer, or open a tracker. It survives tracker visits
   and refreshes. Restart is one click; adjust duration in Practice tools.
4. Tap an athlete’s name. Choose the event, then **Track Skills** or **Track
   Routines**. Opening a tracker starts the practice if needed, without creating
   scores or silently marking attendance.
5. Today’s individual skills and attempt targets stay below the two tracking
   buttons. Children in mixed-level groups keep their own plans.

The main screen no longer has a group dropdown, a separate Open Group button,
a required Start Practice step, a welcome banner, or always-visible review and
editing panels. Practice tools holds attendance corrections, timer duration,
plan editing, private notes/shared feedback links, review, and Finish Practice.

The guided onboarding, group/role permissions, tracker autosave and Undo,
celebrations, review, weekly reports, and email configuration remain available.
An already-finished practice must be explicitly resumed through Practice tools
before further recording. This prevents accidental reopening through a stale
tracker button.

The update checks existing files before changing them and backs up each changed
source file. If a file was independently customized, it stops instead of
overwriting that customization. `--check` performs a read-only preflight.
