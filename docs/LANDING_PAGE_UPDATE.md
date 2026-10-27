# Gym buyer landing page update

Prepared October 27, 2026 against main commit aa0914be467f3146feea1b3cc771c3b395409e49.

## Buyer experience

- Header, hero and closing actions lead to `/demo/`; member signup stays separate.
- The hero describes daily athlete check-ins and ongoing coaching context.
- A read-only preview reuses the actual coach priorities template, with fictional names and check-in examples. No live athlete data is queried for the public preview.
- Director benefits, the check-in → coach review → recorded note workflow, and registration/billing scope are explicit.
- Video playback and coach feedback are separated from experimental, setup-dependent AI analysis. No injury-prevention, competition-scoring or liability-protection claims are made.
- Pricing and pilot enquiries have a public route; no price, free trial, guaranteed setup time or support SLA is invented.

`landing-page-review.html` is a self-contained design review built from the real templates. Styles are embedded; scripts and form submission are disabled. Its welcome page, demo form, pricing and privacy sections can be reviewed without connecting to a database. It is not the deployed website.

## Product enquiries

`/demo/` and `/contact/` accept demo, pricing/pilot, product-support and privacy enquiries without requiring an account. Required details are name, email, topic and permission to reply; gym and message are optional. The UI asks visitors to omit athlete details and passwords.

New enquiries are stored in `accounts.PublicEnquiry`. `/product/enquiries/` is an in-app inbox restricted to active platform superusers, with New / Contacted / Closed statuses and pagination. The link appears in their app navigation. Ordinary staff and gym directors cannot see the platform inbox. The same restriction applies to the Django admin model.

There is **no automatic outbound email or notification**. The platform operator must monitor this inbox and reply through their business email. Sending a form does not book a time, create a membership or create a paid subscription.

Forms use CSRF protection, expiring signed submission IDs, retry deduplication, a honeypot and a three-per-ten-minute session submission limit. The session limit is basic abuse friction, not a distributed or per-person spam guarantee. Submitted details are escaped in the private inbox; public confirmation pages do not disclose them. Enquiry pages are not cacheable.

## Privacy information still requiring operating decisions

The new data/privacy page describes application records, access controls, current provider configuration and the new enquiry handling. It explicitly remains an incomplete privacy policy until the operator confirms:

- Legal operator identity and approved support/privacy contact details.
- Retention and deletion schedules for accounts, athlete records, enquiries, videos and backups.
- Provider regions and contractual arrangements for the deployed environment.
- Gym/guardian consent and the process for access, correction and deletion requests.

No automatic deletion schedule, new data export, marketing email or external recipient has been enabled. The existing terms page is outside this change and remains unfinished. Do not describe the policies as approved or complete.

## Deployment

This update is prepared on a feature branch. Render requires the user to identify a workspace before service inspection or deployment; the available workspace is `My Workspace`. No workspace has been assumed, and production has not been changed.

Before promotion, inspect the intended `newschool-gymnastics-1` service, its deployed source branch, build command and auto-deploy configuration. The existing production release notes identify another service following main; do not unintentionally deploy both.

Migration `accounts.0005_publicenquiry` creates one new table. It does not modify or delete existing users, gyms, surveys, videos or training records. Run normal migrations and `collectstatic --noinput` for the intended service. Preserve all existing database and private-media configuration.

After release, inspect the landing page at desktop and phone widths, send one clearly marked operator test enquiry, verify it in the superuser inbox, and confirm existing member/director signup routes. No live enquiry or production data has been used in development.

## Validation

- 30 focused tests passed on Django 6.1 with isolated SQLite databases: enquiry capture, CSRF, replay deduplication, validation, private inbox permissions and escaping, signup, password recovery, account settings and coach/parent audience behaviour.
- Django system checks and migration consistency checks pass.
- Static collection succeeds with the configured WhiteNoise manifest storage.
- A local static render was inspected; an interactive browser check of this feature build is still outstanding. It does not establish PostgreSQL concurrency or real-device layout behaviour.

Commands (after installing the project requirements):

```bash
python manage.py collectstatic --noinput
python manage.py test accounts.tests_public_enquiries accounts.tests_signup_v2 accounts.tests_recovery accounts.tests coaches.tests_audiences
python manage.py check
python manage.py makemigrations --check --dry-run
```
