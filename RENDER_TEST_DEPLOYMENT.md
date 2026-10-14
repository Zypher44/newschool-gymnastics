# Isolated V2 Render test deployment

Current PyCharm source is imported on branch `staging/v2-render-test`. The dated athlete journal is merged while preserving existing badge routes and navigation. The Pathway fixture is normalized to UTF-8. Docker includes FFmpeg, EGL and GLES libraries.

## Choose one configuration

| Blueprint path | Website | Database | Video worker |
|---|---|---|---|
| `render-test.yaml` | Free | Free, expires after 30 days | None |
| `render-test-full.yaml` | 0.5c-512mb, $7/month | 0.1c-256mb, $6/month | 1c-2g, $25/month |

The default is free core testing. The optional full profile costs roughly $38/month in compute before storage, usage, taxes and workspace/external-storage charges. Obtain approval before applying paid resources and check the actual confirmation screen. These profiles share resource names: apply only ONE Blueprint.

Free web services sleep after 15 minutes without traffic and lack a shell. The workspace shares 750 free instance hours/month. Each workspace can have one free database, which expires after 30 days and has no backups. Core testing covers trackers, practice, badges, journals and reports. Video conversion and AI jobs remain queued without a worker. Full testing includes the separate video worker; 2 GB is a starting allocation to verify using actual videos and memory metrics.

## Storage and initial login

For free core testing, create your director account at `/accounts/signup/director/`. No bootstrap password or other private setup keys are required. The optional bootstrap instructions below apply only to the full profile.

Core-only testing does not require Supabase. Its RENDER_TEST_VIDEOS_ENABLED setting is False: video pages show a paused notice and file uploads are rejected. The storage instructions below apply only when explicitly enabling video testing.

Create a PRIVATE Supabase bucket named `athlete-videos-test`. The test services use the extra `render-test/` prefix. Enter S3 endpoint, access key ID and secret access key in the Blueprint secret fields. Correct the default `ca-central-1` region if your project uses another region. Never commit credentials or paste them into chat.

Set `BOOTSTRAP_TEST_ADMIN_PASSWORD` to a new strong password of at least 12 characters. The first start creates username `v2testdirector`, a director/admin account with an active membership in a new test gym. Subsequent deploys do not reset its password or elevate another account. Once initial setup succeeds, remove both BOOTSTRAP_TEST_ADMIN_USERNAME and BOOTSTRAP_TEST_ADMIN_PASSWORD from the web service environment. Neither is needed after setup.

Local and production accounts/data are not copied automatically. Create sample coach, head coach, athlete and parent accounts and assignments through the test director/admin pages. Initial Pathway definitions can be loaded using `python manage.py loaddata pathway_data.json` from a paid service shell. Importing personal data is a separate action.

## Deployment

Open https://dashboard.render.com/blueprint/new?repo=https://github.com/Zypher44/newschool-gymnastics and select branch `staging/v2-render-test` and your chosen Blueprint path.

Review the new test resources: `newschool-v2-test`, `newschool-v2-test-db`, and (full profile only) `newschool-v2-test-video-worker`. The logical database must be `newschool_v2_test`; settings reject the existing live database. They also require test storage, disable report email delivery, use distinct test cookies and add no-index headers. Auto-deploy is off.

The web service migrates, optionally initializes the test director, collects static files and starts Gunicorn on `$PORT`. The worker waits for migrations, verifies native dependencies and starts both conversion and analysis queues.

Verify the web deploy is live and `/_render-test/health/` returns 200. For full testing, verify the worker separately and submit a real test video. Check all five roles, mobile layouts, timers, autosave/Undo, badge editing/deletion, report privacy, journal history/sharing, and private media across redeploys.

Preparing this branch does not change `main` or redeploy the live service. Production promotion is a separate deployment.

## Primary references

- https://render.com/docs/free
- https://render.com/pricing
- https://render.com/docs/blueprint-spec
- https://render.com/docs/background-workers
