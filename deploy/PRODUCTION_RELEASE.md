# Production upgrade: preserve the existing database

Prepared October 21, 2026. Production has not been changed by preparing this branch.

## Targets

- Live service: `newschool-gymnastics-1`, `srv-dahhaecs728c73b3lj6g`
- Existing URL: https://newschool-gymnastics-1.onrender.com
- Existing database: `newschool_gymnastics_db`, `dpg-dahh8b15efls73bu8h60-a`
- Last live commit: `456f54118cb0db8ba50b1cc752083325a8d5f969`
- Release source: tested staging code at `5b940d39d10842a6f739aa586becda4b84c9d5ed`

Keep the current database, credentials, secret key, cookie configuration, and private
media storage. Do not use `DjangoProject.render_test_settings` or the
`newschool_v2_test` database in production. Do not import staging fixtures or run
`flush`, reset migrations, delete tables, or restore over the live database.
Existing records are retained in place; migrations extend the existing schema.

## Read-only baseline observed

| Record | Count |
| --- | ---: |
| Users | 13 |
| Gym memberships | 12 |
| Athlete profiles | 9 |
| Attendance records | 64 |
| Routine attempts | 851 |
| Routine sessions | 13 |
| Athlete pathways | 7 |
| Athlete pathway requirement statuses | 222 |
| Video references | 4 |
| Approved parent connections | 1 |

Routine sessions and videos have gym IDs. Active non-admin accounts have active gym
memberships. No existing routine attempt is orphaned from an active same-gym athlete
membership. All 851 routine attempts were entered by a head coach. These are point-in-time
observations, not a backup; refresh the baseline immediately before deployment.

## Data migration review

The release adds migration files; existing applied `.py` migration files are unchanged.
New migrations create planner/tracker/journal/report/scheduling tables and add survey,
video, and routine-pressure fields. Stored routine results retain `wow`, `hit`, and
`missed`; the last is relabelled Attempt. Existing attempts default to non-pressure.
Old survey fields are retained; added survey fields do not invent responses.
Legacy media paths remain references to the existing private storage.

`gyms.tests_upgrade_preservation` rehearses the old schema -> new schema with synthetic
accounts, memberships, attendance, routine scores, a survey, a parent link, pathway notes,
and media paths, comparing every original field. This is separate from a PostgreSQL
restore of the real database, which must still be verified before cutover.

Validation completed: 335 application tests passed, including the synthetic legacy
upgrade rehearsal and native video integration. Seven backup-tool guard tests passed.
`makemigrations --check --dry-run` reports no uncommitted model/schema changes.
Tests used isolated SQLite databases; the real PostgreSQL restore rehearsal and
the production cutover are not yet complete.

## Cutover gates

1. Verify a current recoverable production export/PITR checkpoint in Render's database
   Recovery tab. Record its timestamp and availability privately. An export creation
   request is not proof the export finished. The connected Render tools do not expose
   backup/export creation or inspection, so this requires Dashboard or authenticated CLI/API access.
2. Restore that export to an isolated local PostgreSQL 18 database, with outbound email
   and jobs disabled, and rehearse `migrate --plan`, migrations, and record comparisons.
   Never connect this rehearsal to the production database.
3. Inspect production configuration without disclosing secrets. Preserve `DATABASE_URL`,
   `DJANGO_SECRET_KEY`, private storage credentials/bucket, and `DJANGO_DEBUG=False`.
   Confirm `DJANGO_SETTINGS_MODULE` is the base production settings, not render_test_settings.
   Check the runtime still supports the pinned requirements.
4. Account for two services following `main`: the paid live service and an older free
   `newschool-gymnastics` service. Avoid an unintended deploy of the old free service.
   A release branch can be selected only for the intended production service, or the
   obsolete service's auto-deploy can be disabled before merging main. Do not delete it.
5. Deploy only after the gates above. Existing build command installs requirements,
   collects static files, and runs migrations against the existing production database.
   Prefer an explicit pre-deploy migration command on the paid service once configured.
   Do not replace production configuration with the free test Blueprint.
6. Monitor the new deploy until live, inspect migration logs, and verify sign-in and
   representative director/coach/athlete/parent pages. Re-query all baseline counts;
   investigate decreases and verify original record IDs, relationships, and media access.
   Counts can increase with legitimate activity. Confirm reports still display old attempts.
7. Keep the prior commit and recovery point available. Code rollback does not reverse
   database migrations; do not run reverse migrations against new user data as an ad hoc rollback.

## Outstanding operational features

Do not enable outbound report/invitation/reset delivery without verified sender configuration
and a designated test inbox. Do not create a paid AI worker without separate cost authorization;
analysis requests require an actual worker. Production video storage must remain the existing
durable private storage, not the disabled staging backend or an ephemeral filesystem.
