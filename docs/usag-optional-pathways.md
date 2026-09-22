# USAG Optional Pathways (Levels 6–10)

The pathway app now includes a separate **USAG Optional 2026–2030** program for
Levels 6, 7, 8, 9 and 10. The paid 2021–2029 compulsory code was intentionally
left out, so this update does not add Levels 1–5.

The checklist is seeded by migration `0006_seed_usag_optional_levels`. It adds
the four events and 110 coach-facing checklist records: 95 required records and
15 optional composition or bonus review records. The required progress
denominator includes only the required records. Existing High Performance
levels and athlete assessments are preserved.

The source is the supplied **USAG 2026–2030 Optional Code of Points** PDF. The
seed data paraphrases the level composition requirements and records the source
chapter or printed page range beside each item. It is a planning checklist, not
an official scoring or eligibility engine. The supplied copy does not include
the complete floor element catalogue or the vault-value appendices, so coaches
must verify those choices against the current full code and the rules for the
meet being entered.

## How coaches use it

1. Open an athlete in Pathway Manager.
2. Select a current and target level labelled `USAG Level 6` through
   `USAG Level 10`.
3. Open the Pathway Skill Tree and record each item as the athlete develops.
4. Use the optional composition and bonus rows as planning notes. They do not
   increase the required-progress percentage.

The existing HP D-score calculators are hidden and blocked for athletes on a
USAG optional pathway because their start-value rules are different. Parents
see the shared checklist progress and the source limitation notice, while
coach-only notes remain protected by the existing pathway permissions.

After deployment, run:

```bash
python manage.py migrate
```

No fixture upload or background worker is required. The migration is idempotent
and its reverse operation intentionally preserves athlete history.
