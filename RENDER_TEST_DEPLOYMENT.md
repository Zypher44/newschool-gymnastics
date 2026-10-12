# Proposed Render test deployment

This branch is separate from `main`. The deployment configuration is prepared, but the recent V2 application files must be pushed from the current PyCharm project before deployment. The Docker build deliberately stops if the required new source is missing. No Render resources have been created by preparing these files.

## Proposed full-feature setup

| Resource | Name | Proposed plan |
|---|---|---|
| Website | newschool-v2-test | Starter |
| PostgreSQL | newschool-v2-test-db | Basic 256 MB; 1 GB storage |
| Video processing | newschool-v2-test-video-worker | Standard; 2 GB RAM |
| Private media | athlete-videos-test | Separate Supabase bucket |

The worker runs video conversion and AI analysis separately from the website. Standard is a starting allocation for testing, not a measured capacity guarantee. Monitor peak memory, job duration, and upload size before changing plans. The region is provisionally Ohio; use the same Render region for web, worker, and database after checking the actual account setup.

These are proposed paid resources. Confirm current account pricing and the total before applying the Blueprint. Do not apply a paid configuration as an assumed free test. A free web service can test some workflows, but it sleeps while idle, has no shell, and cannot host a free background worker. A free Render database is limited to one per workspace and expires after 30 days. See current Render documentation below.

## Latest code first

The remote `v2-integration` branch was last updated on 28 September 2026 when this setup was prepared. It lacks the recent practice_focus, skill_tracker, practice_hub, and journal features. Do not deploy that old snapshot as the new version.

Start by checking the current PyCharm project:

```powershell
git status --short --branch
```

If this project is already a Git checkout of Zypher44/newschool-gymnastics, integrate the prepared branch while preserving current local edits and push the complete tested application to `staging/v2-render-test`. Inspect the exact file list before committing. Do not commit `.env` files, passwords, local databases, uploaded athlete media, virtual environments, IDE files, or patch backup folders.

If the current project is a downloaded ZIP without Git history, use a clean checkout of the staging branch and copy only the tested application source and required public/model assets into it. Keep deployment files from this branch. The old repository has tracked media/IDE files: do not add or update those personal/runtime files during the source transfer. Do not use force push to bypass a conflict.

The MediaPipe model belongs at `video_library/ai/models/pose_landmarker_full.task`. The full application should include all new migrations, templates, static files, and practice apps. `manage.py` remains the existing Django launcher; the local PostgreSQL launcher is not used on Render.

## Storage and configuration

Create a private Supabase bucket named `athlete-videos-test`. Configure its S3 endpoint, access key ID, secret access key, and actual region only inside the test Render environment. Existing production bucket settings must not be copied unchanged. This setup checks the bucket name and uses an additional `render-test/` object prefix.

Use the separate database named `newschool_v2_test`. The test settings reject a different database name, local SQLite, missing cloud storage, or DEBUG=True. Never populate the test database by pointing it at the live database. Begin with fresh test accounts and records. Importing local or production records is a separate action that has not been requested here.

The Blueprint generates a new Django secret and uses distinct test session/CSRF cookie names. It leaves report email delivery unconfigured so test reports cannot be sent through the production provider. The test response headers discourage search indexing; the site is still an internet-accessible login-protected app, not a private network service.

## Apply only after source and account access are ready

Use Render Blueprint path `render-test.yaml` from `staging/v2-render-test`. Review the three new resources and costs before applying. Auto-deployment is off. The web service migrates the test database and collects static files before starting Gunicorn. The worker waits for those migrations, checks its native video dependencies, and starts both queues.

The health endpoint is `/_render-test/health/`. It returns only environment/readiness status and verifies a database connection. Confirm the web service and worker deploys independently; a healthy website does not establish that video processing works.

## Initial test accounts and checks

Use the new service's Render shell to create test accounts; existing local logins do not transfer automatically. A director must have an active membership in the test gym. Create head coach, coach, athlete, and parent test accounts and their assignments/approved links through the director/admin pages. Do not reuse production passwords.

Check all five roles, mobile layouts, independent timers, trackers/Undo, badges, report privacy, journal history/sharing, and video upload/conversion/analysis. Confirm private files survive a redeploy and unauthorised users cannot view another athlete or gym. Check the worker logs without exporting credentials or full private records.

Record the deployed commit and URLs. Promote a tested commit to production only as a separate requested deployment. Keep `main` and the live service unchanged during this test setup.

## Official references

- https://render.com/docs/deploy-django
- https://render.com/docs/blueprint-spec
- https://render.com/docs/free
- https://render.com/docs/background-workers
- https://render.com/pricing
