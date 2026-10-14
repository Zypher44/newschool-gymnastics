# Report email setup

The patch adds Email Report beneath Print Report on Weekly Progress, Athlete
Progress, Team Readiness, Attendance, Wellness, Testing, and Skill Progress.
The five Report Center placeholder pages now open a report preview with real data.

Emails are sent only when a coach explicitly selects recipients and presses Send.
This patch does not schedule weekly emails or send any existing reports at installation.
Weekly reports must be published before they can be emailed.

## Activate delivery

1. Create a Resend account at https://resend.com and verify a domain you own.
   Domain verification guide: https://resend.com/docs/dashboard/domains/introduction
2. Create an API key with permission to send from that domain.
3. Add these environment variables to the Render web service, then redeploy:

   - `RESEND_API_KEY`: your API key (never put it in source code or Git).
   - `REPORT_EMAIL_FROM`: for example `Winstar Gymnastics <reports@your-domain.ca>`.
   - `REPORT_EMAIL_APP_URL`: your app's public HTTPS URL. On Render this can use
     RENDER_EXTERNAL_HOSTNAME automatically if the explicit setting is omitted.

The sender address must use your verified domain. The resend.dev test sender is
restricted and is not suitable for emailing your parents.

For local PyCharm testing, add the same variables to the Run Configuration's
Environment variables, or set them in PowerShell before starting run_v3_local.py.
Restart the server after changing environment variables. Use the public HTTPS
app URL for the links in messages, even while testing on localhost.

Install from the folder containing manage.py:

    python apply_v3_report_email_delivery.py
    python run_v3_local.py migrate
    python run_v3_local.py check
    python run_v3_local.py runserver

After deploying to Render, apply migrations there using your normal deployment process.

## Using it

Select the athlete and date range. Click Email Report beneath Print Report.
Review the saved email copy and the displayed recipients, then send.
Individual reports can go to approved linked parents or the authoring coach.
An all-athlete report can go only to the authoring coach's own account email.
Parents without valid account emails are skipped; update those accounts first.
No free-text recipient input is provided.

The parent-safe copy contains attendance totals, wellness averages, verified
testing, approved skill/routine attempts, milestones, and explicitly shared feedback
as appropriate to the report. It excludes private coach, testing, skill, and survey
notes, videos, and the legacy Coach Notes section. Non-weekly email copies omit group
comparisons. Weekly copies follow the coach's group-average privacy setting.

Emails are separate for each parent, so their addresses are not exposed to one another.
The delivery history shows submission to Resend, not confirmed receipt in an inbox.
For inbox delivery or bounce details, check your Resend dashboard.

## Retry behavior

Up to two recipient emails are submitted per request to keep web requests short.
If more are pending, press Send again to continue. Submitted messages are skipped.
Each message has a stable provider idempotency key and fixed content. Resend retains
keys for 24 hours; this patch limits uncertain retries to 23 hours. If a confirmation
is still unknown after that window, check Resend before making a new preview.
Do not refresh/republish a weekly report just to retry an email: use the same preview.
Changing a report, hiding its group averages, or withdrawing it blocks stale email previews.
An email already submitted cannot be recalled by withdrawing the report in the app.

Official references:
- https://render.com/docs/free
- https://resend.com/docs/api-reference/emails/send-email
- https://resend.com/docs/dashboard/emails/idempotency-keys
