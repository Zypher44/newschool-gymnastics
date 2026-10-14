# Athlete practice journal

Stop your local server, save `apply_v3_athlete_journal.py` beside `manage.py`, and run:

```powershell
python apply_v3_athlete_journal.py
python run_v3_local.py migrate
python run_v3_local.py runserver
```

Hard-refresh with Ctrl+F5. Athletes can open **My Practice Journal** from Athlete Home or their navigation. Coaches and parents can open **Shared Journals** from their navigation. Journal links also appear on the progress pages.

## Writing and history

- One journal entry per athlete, gym, and practice date.
- Today is selected for a new entry. Athletes can select an earlier date to record an older practice.
- Choose Great, Okay, or Tough, or answer at least one prompt: My win today; Something I found challenging; What I want to work on next.
- Answers are optional, up to 1,500 characters per prompt. Use **Save my entry** to save; journal text does not autosave.
- **Past entries** lists entries by practice date, newest first. Use From/To filters and Older entries to find earlier entries.
- **Read entry** opens the full reflection with its practice date and first-saved/last-updated timestamps.
- **Edit** changes an existing entry while retaining its original practice date. Opening today's form again resumes today's entry.
- If another tab saved the same date first, the latest entry is kept and the submitted draft stays on the page. Open the saved entry before editing again.
- The browser is asked to warn before leaving a changed form. No journal answers are put into local storage.

## Sharing

New entries start as **Only me**. Two independent boxes allow sharing the whole entry with coaches and/or approved linked parents. The athlete can change these choices later. Turning sharing off removes further access, but cannot undo something another person has already read.

Coaches and parents can only read shared entries; they cannot create or edit an athlete's journal. Head coaches can read entries shared with coaches for active athletes in their gym. Regular coaches need an athlete assignment or an active assigned training group. Parents need an approved child connection in the same active gym. Directors do not receive journal access.

Journal reflections are separate from wellness surveys, coach notes, skill/routine scores, badges, weekly reports, and email reports. Saving a journal does not award a badge, record attendance, or alter practice results. There is no automatic journal publishing or email delivery.

## Installation details

The update adds migration `practice_focus/0010_athletejournalentry.py`; run the migration before opening journal pages. No new Python package is required. The installer backs up replaced files under `.v3-backups/athlete-journal/` and checks all replacements before writing. It preserves unrelated edits when patch contexts match; overlapping edits stop the installer before changes.

If another migration already occupies the next practice_focus migration number, the installer stops so the migration can be merged for that project. Send the complete terminal output in that case.

Optional preview:

```powershell
python apply_v3_athlete_journal.py --check
```

Optional checks using the local database configuration:

```powershell
python run_v3_local.py test practice_focus.tests_journal
```

Verification in the isolated development environment covers dates/history, editing, stale tabs, repeat saves, sharing/revocation, approved parent links, coach assignments, gym boundaries, CSRF, and HTML escaping. Check the final layout and tap flow on your own phone after installation.
