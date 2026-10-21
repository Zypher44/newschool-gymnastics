# Practice refinements

1. Smaller attendance/group timer panel.
2. Group timer Start/Stop preserves remaining time. Timer length is in Practice tools.
3. Each child has an independent event, duration and Start/Stop timer beneath their name.
   Timers persist in the database, continue while running on another page, and freeze when stopped.
   A stopped timer resumes its remaining time. Changing its event/duration starts a fresh countdown.
   Starting an expired timer starts a new countdown. Finishing practice stops every timer.
4. Routine autosave/Undo remains active; its status panel stays in the normal page footer.
5. Start Practice selections and planner forms update without a full reload, using the same
   Django validation, permissions and CSRF protection. Unsaved plans are protected before switching.
   Tracker buttons still navigate to their respective pages. Without JavaScript, forms work normally.
6. Start Practice (🚀) and Practice Planner (🎯) sit under Performance; dashboard has Start Practice.
7. Getting Started lives in Account Settings for directors, coaches, athletes and parents.

## Install
Stop the local server. Save the updater beside manage.py and run:
python apply_v3_practice_refinements.py
python run_v3_local.py migrate
python run_v3_local.py check
python run_v3_local.py runserver
Hard refresh with Ctrl+F5. The installer backs up changed source files before writing.
Use --check for a dry run. It refuses to overwrite unexpected customized source.
Existing practice plans, results, attendance and onboarding records remain intact.
Email delivery configuration is unchanged.

## Validation
91 isolated Django checks cover timers, roster permissions, CSRF, attendance, tracker results,
reports, email integration and onboarding. Nine JavaScript DOM interaction checks cover partial
navigation, independent countdowns, plan validation/unsaved edits, network failures and footer styling.
Actual device layout still needs a check on your local/Render deployment.
