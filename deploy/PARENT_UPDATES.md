# Parent updates and daily check-ins

Apply the normal Django migrations. Existing surveys stay version 1 with all historical answers intact. New check-ins are version 2; unasked stress, soreness, and sleep-hour measurements are null rather than fabricated scores.

Parents can select only approved linked athletes. Connection requests use the active gym roster, date-of-birth verification, and director approval. Attendance notices are planned absences/lateness; they never modify actual AttendanceRecord rows.

Communication preferences apply to future routine in-app notifications and coach-sent report emails. Direct messages and account/system notices remain available. Defaults preserve existing delivery behavior. Weekly email choices queue reports for a combined link summary.

Email remains disabled on the free test site. Once email delivery is enabled in an authorized environment, configure an existing scheduler to run `python manage.py deliver_parent_digests` daily using the same settings and database. Each parent receives a summary at most once in seven days. Do not provision a paid Render service without authorization. Pending retries reuse the original provider idempotency token and payload; stale or uncertain batches older than 23 hours are blocked for review. Revoked links, withdrawn reports, changed coach access, and email opt-outs are rechecked before delivery.

No digest command is run during deployment.
