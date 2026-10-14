# Practice Passport

Coaches: Reports > Practice Passports. Choose an athlete, then a stamp. Measurable
stamps show progress from coach-approved tracker results and recorded attendance.
Choose the achievement date, optionally add a shared message, confirm, and award.
Learning, teamwork, personal improvement and weekly growth stamps use coach observation.
Every stamp is explicitly awarded by a coach; opening a page never grants awards.

11 badge families / 18 stamps:
- My First Practice: first date with approved tracker results; coach confirms completion.
- Goal Getter: Bronze 3, Silver 10, Gold 25 completed planned skill/routine target tasks.
- Correction Detective: coach recognizes an applied correction.
- My Wow Moment: first approved Wow in the skill or routine tracker.
- Better Than Before: coach recognizes an individual improvement milestone.
- Routine Builder: planned regular routine target met on three practice dates.
- Ask & Learn: coach recognizes seeking help and applying the learning.
- Great Teammate: coach recognizes helping or encouraging a teammate.
- Event Explorer: one stamp each for Vault/Bars/Beam/Floor, from a completed planned target.
- Growing Every Week: coach confirms individual goals met in three training weeks,
  accounting for the child's schedule and planned breaks.
- Practice Pal: Bronze 5, Silver 15, Gold 30 recorded Present/Late practices.

Attendance is cumulative; absences and breaks never reset it. Attendance eligibility
uses records entered by coaches with membership in the child's current gym. Pending,
rejected and undone tracker entries are excluded from measurable badge eligibility.
Backdated awards use evidence through the selected achievement date. All messages on
awards are shared with the child and approved linked parents. Withdrawal reasons and
coach audit history stay private. Duplicate awards do not create duplicate stamps.
An authorized coach can withdraw an accidental stamp without deleting its history.
Each tier/event stamp is individually selected and awarded by a coach.

Athletes and approved linked parents: Practice Passport in navigation, or the passport
link on progress/report pages. Athletes can open new stamps one at a time, with the
existing confetti/sound system. Stamps already opened are remembered per account,
gym and athlete in that browser. With blocked browser storage, celebrations still
work but may appear again after a refresh. Motion follows reduced-motion settings.
Parents can view shared stamps and personal progress, with no award/withdraw controls.

## Install
Stop the local server. Install earlier practice/report/email patches first.
Save apply_v3_practice_passport.py beside manage.py and run:
python apply_v3_practice_passport.py
python run_v3_local.py migrate
python run_v3_local.py check
python run_v3_local.py runserver
Hard-refresh with Ctrl+F5. The updater adds practice_focus migration 0007.
It backs up source changes and supports --check. It preserves unexpected custom files
by stopping preflight before changes. Existing plans, scores and timers are unchanged.
No email is sent by this update. The passport is shared within the application.

## Verification
13 isolated Django tests cover all 18 stamps, eligibility, pending result exclusion,
attendance, dates, duplicate awards, withdrawals/re-awards, audit privacy, CSRF,
roster/gym access and family permissions. Five DOM/style checks cover coach selection,
new-stamp celebrations, repeat suppression, blocked browser storage and parent views.
Existing linked-event/timer and role-navigation checks also pass. Device layout should
be checked on your local deployment; no physical-device browser checks were run here.
