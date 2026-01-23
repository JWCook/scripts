#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""Import and export permission exceptions from Firefox-based browsers.

This is useful if you have a policy of clearing/blocking cookies by default, except for specific
hosts in a whitelist. These settings are stored in a SQLite db, which isn't included in firefox
sync.
"""

import sqlite3
from argparse import ArgumentParser
from configparser import ConfigParser
from pathlib import Path
from time import time

EXPORT_PATH = Path(__file__).parent / 'ff_exceptions.txt'
BROWSER_DIR = Path('~/.librewolf').expanduser()


def find_profile_dir() -> Path | None:
    """Find path of Firefox default profile"""

    # Get profile name from profiles.ini
    config = ConfigParser()
    config.read(BROWSER_DIR / 'profiles.ini')
    for section in config.sections():
        if section.startswith('Install') and 'Default' in config[section]:
            return BROWSER_DIR / config[section]['Default']
    return None


def test_locked(db_path: Path):
    """Test if the SQLite db is locked (likely means browser is still open)"""
    try:
        conn = sqlite3.connect(db_path, timeout=0.1)
        conn.execute('BEGIN IMMEDIATE')
        conn.rollback()
        conn.close()
    except sqlite3.OperationalError as e:
        if 'locked' in str(e).lower():
            raise RuntimeError(f'DB locked: {db_path}\n\tEnsure browser is closed') from None
        raise


def import_hosts(db_path: Path, export_path: Path):
    """Import permission exceptions from repo to Librefox"""
    if not export_path.exists():
        print('Nothing to import')
        return

    print(f'⬇️ Importing to {db_path}')
    conn = sqlite3.connect(db_path)
    hosts = export_path.read_text().splitlines()
    for host in hosts:
        exists = conn.execute(
            "SELECT id FROM moz_perms WHERE origin=? AND type='cookie'", (host,)
        ).fetchone()
        if exists:
            continue

        unix_time_ms = int(time() * 1000)
        print(f'Adding {host}...')
        conn.execute(
            'INSERT INTO moz_perms '
            '(origin, type, permission, expireType, expireTime, modificationTime)'
            "VALUES (?, 'cookie', 1, 0, 0, ?)",
            (host, unix_time_ms),
        )
    conn.commit()


def export_hosts(db_path: Path, export_path: Path):
    """Export permission exceptions from Librefox to repo"""
    print(f'⬆️ Exporting from {db_path} to {export_path}')
    conn = sqlite3.connect(db_path)
    results = conn.execute("SELECT origin from moz_perms WHERE type='cookie';")
    with export_path.open('w') as f:
        hosts = sorted([row[0] for row in results])
        f.write('\n'.join(hosts) + '\n')


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-p',
        '--profile-dir',
        default=find_profile_dir(),
        help='Browser profile directory',
    )
    parser.add_argument(
        '-e',
        '--export-path',
        default=EXPORT_PATH,
        help='Path to file containing hosts to sync',
    )
    args = parser.parse_args()

    profile_dir = Path(args.profile_dir).expanduser()
    if not profile_dir or not profile_dir.exists():
        raise ValueError('Profile dir not found')
    export_path = Path(args.export_path).expanduser()
    export_path.parent.mkdir(parents=True, exist_ok=True)

    db_path = profile_dir / 'permissions.sqlite'
    test_locked(db_path)
    import_hosts(db_path, export_path)
    export_hosts(db_path, export_path)


if __name__ == '__main__':
    main()
