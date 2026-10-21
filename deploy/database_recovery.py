"""Manual PostgreSQL backups and non-destructive restore drills. No Django required.

Connection URLs come only from NS_BACKUP_DATABASE_URL / NS_RESTORE_DATABASE_URL.
Install PostgreSQL client tools matching the server major version (18 for staging).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit, parse_qs


def connection(variable):
    raw = os.environ.get(variable, '')
    try:
        url = urlsplit(raw)
        if url.scheme not in ('postgres', 'postgresql') or not url.hostname or not url.path.strip('/'):
            raise ValueError
        port = url.port or 5432
    except ValueError:
        raise ValueError(f'Set {variable} to a valid PostgreSQL connection URL.') from None
    env = os.environ.copy()
    # Clear ambient libpq connection/service overrides before selecting a DB.
    for key in list(env):
        if key.startswith('PG'):
            env.pop(key)
    env.update(PGHOST=url.hostname, PGPORT=str(port), PGDATABASE=unquote(url.path[1:]),
               PGUSER=unquote(url.username or ''), PGPASSWORD=unquote(url.password or ''),
               PGSSLMODE='require', PGCONNECT_TIMEOUT='15')
    ssl = parse_qs(url.query).get('sslmode', ['require'])[0]
    if ssl == 'disable':
        if url.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('TLS cannot be disabled for a remote database.')
        env['PGSSLMODE'] = 'disable'
    if ssl in ('verify-ca', 'verify-full'):
        env['PGSSLMODE'] = ssl
    return env


def run(args, env):
    try:
        result = subprocess.run(args, env=env, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise ValueError(f'{args[0]} is not installed. Install PostgreSQL client tools.') from None
    except subprocess.CalledProcessError:
        # libpq errors can include sensitive host/user information. Do not print them.
        raise ValueError(f'{args[0]} failed. Check connectivity, permissions, and client/server versions locally.') from None
    return result.stdout.strip()


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def backup(path):
    env = connection('NS_BACKUP_DATABASE_URL')
    path = Path(path).resolve()
    manifest = Path(str(path) + '.json')
    if path.exists() or manifest.exists():
        raise ValueError('Choose a new backup filename; existing backups are never overwritten.')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against accidentally replacing a symlink.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        run(['pg_dump', '--no-password', '--format=custom', '--no-owner', '--no-acl',
             '--file', str(path)], env)
        if path.stat().st_size == 0:
            raise ValueError('The backup archive is empty.')
        run(['pg_restore', '--list', str(path)], env)
        record = {'created_at': datetime.now(timezone.utc).isoformat(),
                  'sha256': digest(path), 'bytes': path.stat().st_size,
                  'restore_tested': False}
        with manifest.open('x') as stream:
            os.chmod(manifest, 0o600)
            json.dump(record, stream, indent=2)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    print('Backup archive and checksum created. Store both securely off the server. Restore is not yet tested.')


def restore_check(path):
    source = connection('NS_BACKUP_DATABASE_URL')
    target = connection('NS_RESTORE_DATABASE_URL')
    if (source['PGHOST'], source['PGPORT'], source['PGDATABASE']) == (
            target['PGHOST'], target['PGPORT'], target['PGDATABASE']):
        raise ValueError('Restore target must differ from the source database.')
    if not target['PGDATABASE'].endswith('_restore_check'):
        raise ValueError('Use a separately created empty database ending in _restore_check.')
    path = Path(path).resolve()
    manifest = Path(str(path) + '.json')
    record = json.loads(manifest.read_text())
    if digest(path) != record['sha256']:
        raise ValueError('Backup checksum mismatch; restore stopped.')
    # Never use --clean or replace a populated database, even for a drill.
    count_sql = "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','S','f');"
    count = run(['psql', '--no-password', '-X', '-At', '-v', 'ON_ERROR_STOP=1', '-c', count_sql], target)
    if count != '0':
        raise ValueError('Restore target is not empty; no data was changed.')
    run(['pg_restore', '--no-password', '--exit-on-error', '--single-transaction',
         '--no-owner', '--no-acl', '--dbname', target['PGDATABASE'], str(path)], target)
    run(['psql', '--no-password', '-X', '-At', '-v', 'ON_ERROR_STOP=1', '-c',
         'SELECT count(*) FROM django_migrations;'], target)
    print('Restore completed in the isolated database. Verify login, record counts, and representative workflows before signing off recovery.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore-check'])
    parser.add_argument('archive', help='Local path on a secure, durable drive')
    args = parser.parse_args()
    try:
        (backup if args.action == 'backup' else restore_check)(args.archive)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
