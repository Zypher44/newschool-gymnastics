# V2 pilot readiness — October 21, 2026

Scope: `staging/v2-render-test` and the free `newschool-v2-test` service only.
Production has not been changed. This document is an evidence log and release
checklist, not a statement that the platform is ready for public launch.

## Confirmed blockers before storing irreplaceable pilot data

| Item | Current evidence | Required next step |
| --- | --- | --- |
| Database retention | Render reports the free staging database expires November 13, 2026 at 3:44 p.m. Eastern. Free PostgreSQL has no managed backups. | Export the data before expiry; choose durable hosting before a real club pilot. No paid resources have been created. |
| Recovery | Backup and isolated restore commands are prepared and their refusal checks tested. No live database archive or successful PostgreSQL restore has been produced in this audit. | Run an actual export and restore drill using PostgreSQL 18 client tools, then validate restored records and login. |
| Email | Test settings explicitly disable provider delivery. No messages have been sent during this audit. | Configure a verified sender and canonical HTTPS app URL in the intended environment; test delivery to a designated test inbox. |
| Privacy and terms | `/privacy/`, `/terms/`, and `/cookies/` identify themselves as placeholders. | Confirm operator/contact details, purposes, providers, retention/deletion, access requests, consent, and appropriate review before publication. Do not describe these placeholders as completed policies. |
| Videos | Test middleware disables uploads; persistent media is not configured for this environment. | Keep videos disabled for the core pilot, or explicitly arrange private durable storage and re-test authorization before enabling. |
| Support | Signed-in users can message their director; public support falls back to the gym's usual contact details. | Confirm the product support contact and issue triage owner. Do not publish a guessed email address. |

Render source references checked October 21, 2026:
- https://render.com/docs/free#30-day-limit
- https://render.com/docs/postgresql-backups

## Backup and restore drill

1. Install PostgreSQL 18 `pg_dump`, `pg_restore`, and `psql` on a trusted machine.
   The client tools must be compatible with the server. Keep connection URLs in
   private environment variables, not Git, screenshots, command arguments, or chat.
2. Set `NS_BACKUP_DATABASE_URL` to the staging database's external connection URL.
   Remote connections require TLS. The current external IP allowlist is empty;
   a narrowly scoped access rule may be needed for the operator's machine. Do not
   open all addresses merely to perform this drill.
3. Create an export on a secure, durable drive:

   ```text
   python deploy/database_recovery.py backup /secure/backups/v2-staging.dump
   ```

   The command refuses overwrite, validates the archive listing, and writes a
   SHA-256 sidecar. Neither successful export nor a checksum proves recovery.
   Restrict folder access/Windows ACLs and encrypt the drive or archive. The dump
   contains personal data and password hashes. Never commit it or attach it to a bug report.
4. Separately create an empty database named, for example, `v2_restore_check`.
   Give the drill user access to this database only. Set `NS_RESTORE_DATABASE_URL`
   to that database. A local-only server without TLS may use `?sslmode=disable`;
   remote targets cannot disable TLS.
5. Run:

   ```text
   python deploy/database_recovery.py restore-check /secure/backups/v2-staging.dump
   ```

   This refuses the source database, target names without `_restore_check`, any
   target with existing user relations, and a checksum mismatch. Restore uses one
   transaction and never uses `--clean`. Run the drill with exclusive access to
   the isolated target. It may require creating a fresh empty target after a failed drill.
6. Point an isolated local app at the restored database with outbound delivery
   and background jobs disabled. Compare migration/account/gym/attempt counts,
   then inspect representative reports, journals, approved family connections,
   and login. Database backups do not include uploaded video files; those require
   their own storage recovery procedure.
7. Record the archive checksum, date, restore target, validation outcome, operator,
   and recovery duration in a private operations log. Store a second encrypted
   copy off the app server. Choose a backup frequency and retention policy before
   the real pilot; no recurring backup has been scheduled by this audit.

## Account access and email

- The sign-in page now links to Forgot your password. Existing accounts need an
  exact username and matching email. Shared family emails reset only the requested
  username. Inactive users and accounts without usable passwords do not get a reset;
  imported accounts continue to use their director-issued setup link/invitation.
- Recovery uses the existing HTTPS email provider. It never logs a reset link to
  the console when email is disabled; the page directs users to their gym director.
- Base settings read `RESEND_API_KEY`, `REPORT_EMAIL_FROM`, and `REPORT_EMAIL_APP_URL`.
  Test settings intentionally clear these; changing environment variables alone
  does not enable email on the free staging site. Enabling test delivery requires
  a separate explicit configuration change.
- The canonical app URL is used for reset links. Generic responses avoid revealing
  account existence. Requests are limited to five per account and originating
  server-observed IP per 15 minutes in the configured Django cache. Before scaling
  beyond one process, configure a shared cache and verify proxy-aware rate limiting.
- Delivery QA still required: invitation, reset, weekly summary, and manually emailed
  report; inbox/spam placement; invalid address/provider failure; expired/used links;
  new-password login and old-session invalidation. Use designated test accounts.

## Permissions and practice QA

Automated coverage includes gym isolation, assigned coach access, approved parent
connections, private journals, sibling selection, report visibility, CSRF, and
notification ownership. Passing tests are evidence, not an exhaustive security review.

Audit validation: all 334 Django application tests passed using an isolated SQLite
test database, including the native video integration test after loading the local
graphics library. Seven standalone backup-tool safety tests passed. Email delivery
was mocked for recovery tests; no live email, database export, or restore drill was
performed. No schema migration is required for this patch.

Before inviting clubs, run with designated pilot accounts and record actual results:

- Director, head coach, coach, athlete, and parent each sign in on phone and desktop.
- Users from a second test gym cannot read or edit the first gym's records by URL/ID.
- A parent sees only approved children; revoking approval removes access. Private
  journal entries and private coach notes remain unavailable to parents/other athletes.
- Two real devices score the same athlete/event simultaneously. Confirm exact saved
  counts; retry after a network interruption; undo one attempt without removing
  another user's entry; ensure refresh does not lose saved progress.
- Start, pause, resume, and extend group/individual timers. Changing one child's
  event/timer must not change another child's timer. Test backgrounding the phone.
- Check attendance, plan editing conflicts, parent absence notices, report date
  ranges, and sibling selection across all parent pages.

SQLite tests do not prove PostgreSQL locking/concurrency behavior or mobile layout.
The human multi-device practice drill is still outstanding.

## Privacy, support, and release decision

Before publishing policies, obtain the operator's approved support/privacy contact,
retention/deletion schedule (including exports/backups), intended hosting/provider
list, consent approach for minors/videos, and a process for access/correction/deletion
requests. Confirm who may see daily check-ins, private talk requests, coach feedback,
and journal sharing. Do not claim a compliance certification from automated tests.

Pilot bug reports should include role, page, steps, expected/actual behavior, device,
time, and a redacted screenshot. Exclude passwords, reset links, survey/journal text,
and unnecessary child information. Route sensitive issues privately to the operator.

Release gate: only mark ready after real backup/restore, durable hosting, configured
delivery, approved policies, designated support, and multi-device practice QA are
recorded. Keep production unchanged until a separate production deployment request.
