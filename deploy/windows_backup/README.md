# NewSchool PC backup setup (Windows)

Prepared for the **free test database only**, `newschool_v2_test`. It does not
change or restore production. Setup has not been run on your PC yet.

## Before setup

- Use your normal Windows account (the one you will stay signed into).
- Have Python 3.10+ and PostgreSQL **18 client tools** installed. No Python packages
  or running local PostgreSQL server are required just to save a backup.
- Keep Windows drive encryption/BitLocker enabled where available. The database
  connection is protected with your Windows account's DPAPI encryption; **database
  archives themselves are not encrypted by this package**. They contain personal
  data and password hashes. The installer restricts the folders to you and SYSTEM;
  keep a second encrypted copy on an external drive. Do not email/upload dumps.
- On Render, open **newschool-v2-test-db**, then its connection/access settings.
  Permit your PC's current public IPv4 address as a single `/32` entry for external
  access. Do not replace existing rules or add `0.0.0.0/0`. A changing home IP will
  need an updated rule. This setup does not modify Render network access.
- Copy the **External Database URL** for `newschool_v2_test`. Keep it out of chat,
  screenshots, source code, and your terminal command history. The installer asks
  for it through a hidden prompt; do not put it in the command below.

## Install once

1. Extract the entire ZIP into a folder. Do not run scripts from inside the ZIP.
2. Open Windows PowerShell in the extracted folder (Explorer address bar: type
   `powershell` and press Enter).
3. Run this single command:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-NewSchoolBackup.ps1
   ```

   This bypass applies only to this invocation, not your machine-wide execution
   policy. Review the scripts before running. If organizational policy blocks it,
   ask your IT administrator; do not weaken organization policy.
4. Paste the external TEST URL at the hidden prompt. It will not echo on screen.
5. Setup runs a real first backup. **It registers/enables the scheduled task only
   if that succeeds.** If setup fails, fix the indicated prerequisite/access issue
   and run it again. Re-running setup disables an existing package task until the
   new first backup succeeds. It replaces the saved credential/configuration but
   does not delete existing archives during installation.

Default: **8 p.m. PC local time**, plus an additional backup when you sign into Windows.
Scheduled runs always attempt a fresh backup; signing in more often may create
additional copies. A manual run without `-Force` skips if a backup succeeded
within 12 hours. Your PC must be on, awake,
online, and signed in; a locked screen is fine. This task does not wake the PC or
run after signing out. A missed schedule can catch up once you are signed in and
the machine/network are available. Task failures retry twice at 15-minute intervals.
The newest 30 checksum-validated successful archives are retained; older validated
archives are deleted only after a new export succeeds. Unverified/partial files
are left in place for manual review. This is a count limit, not exactly 30 days.

To choose another time or retention count at installation:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-NewSchoolBackup.ps1 -DailyTime '19:30' -KeepBackups 45
```

## Where to look

- Archives and `.json` checksums: `%USERPROFILE%\NewSchoolBackups`
- Private configuration and status: `%LOCALAPPDATA%\NewSchoolBackup`
- Latest result: `last-run.json`; last successful export: `last-success.json`
- Windows Task Scheduler task: **NewSchool - Daily Test Database Backup**

To run another backup immediately:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\NewSchoolBackup\Run-NewSchoolBackup.ps1" -Force
```

Check the file dates and `last-run.json` regularly. No email alert is configured.
A successful export is **not** proof of recovery. The included
`database_recovery.py` supports `restore-check` into a separately created empty
database ending `_restore_check`; follow `RESTORE-AND-LAUNCH-CHECKLIST.md`.
Never restore over the live database. Uploaded videos are not included in the dump.

## Pause or remove the daily task

```powershell
Disable-ScheduledTask -TaskName 'NewSchool - Daily Test Database Backup'
Unregister-ScheduledTask -TaskName 'NewSchool - Daily Test Database Backup' -Confirm
```

Those commands do not delete your archives. The saved connection can only be
decrypted under the same Windows user/machine context. Run setup again if you
change PCs, Windows profiles, or the database password.

## Current limitation

The free Render database expires **November 13, 2026**. A PC copy preserves an
export; it does not keep the cloud database or website running after expiration.
An actual first export, Windows scheduled run, and isolated restore drill still
need to be completed on your machine. No scheduled task has been created remotely.

Implementation references:
- https://learn.microsoft.com/powershell/module/microsoft.powershell.security/convertfrom-securestring
- https://learn.microsoft.com/powershell/module/scheduledtasks/new-scheduledtasksettingsset
- https://learn.microsoft.com/powershell/module/scheduledtasks/register-scheduledtask
