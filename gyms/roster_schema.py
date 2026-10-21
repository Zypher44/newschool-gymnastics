"""Stable columns shared by the roster template, importer, and exporter."""
SCHEMAS = {
    'Athletes': ['roster_id', 'username', 'first_name', 'last_name', 'email', 'phone', 'date_of_birth', 'level', 'groups'],
    'Parents & Guardians': ['roster_id', 'username', 'first_name', 'last_name', 'email', 'phone', 'athlete_ids', 'relationship'],
    'Coaches': ['roster_id', 'username', 'first_name', 'last_name', 'email', 'phone', 'role', 'groups'],
}
ROLES = {'Athletes': 'athlete', 'Parents & Guardians': 'parent'}
INSTRUCTIONS = [
    ['NewSchool Gymnastics roster setup', ''],
    ['Step', 'What to do'],
    ['1', 'Fill the three roster tabs. Keep the header row unchanged.'],
    ['2', 'Use unique roster IDs: A001, P001, C001. Keep IDs unchanged for repeat imports.'],
    ['3', 'Link parents with athlete_ids. Separate multiple IDs or groups with semicolons.'],
    ['4', 'Use YYYY-MM-DD for dates of birth. Coaches role must be coach or head_coach.'],
    ['5', 'New usernames are optional. For existing people, keep their exported username.'],
    ['6', 'Blank cells preserve existing values. Imports never remove people, groups or family links.'],
    ['7', 'Review the preview. Existing details change only when you explicitly enable updates.'],
    ['8', 'No passwords belong in this file. New accounts receive password setup invitations separately.'],
    ['Google Sheets', 'Open in Google Sheets, then download as Excel (.xlsx). Or upload the three tabs as CSV files.'],
    ['Example athlete', 'A001; Alex Taylor; date_of_birth=2015-04-12; groups=Team A'],
    ['Example parent', 'P001; Sam Taylor; sam@example.com; athlete_ids=A001; relationship=Guardian'],
    ['Example coach', 'C001; Jo Lee; jo@example.com; role=head_coach; groups=Team A'],
]
