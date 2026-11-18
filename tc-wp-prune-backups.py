#!/usr/bin/env python3
"""Prune TC WordPress snapshots: at most 10, at most 6 calendar months old.

Only immediate directories in BACKUP_ROOT matching YYYYmmdd-HHMMSS-PID are eligible.
No symlinks are followed. Never touches unrelated backup folders.
"""
import calendar
import re
import shutil
import stat
import sys
from datetime import date, datetime
from pathlib import Path

PATTERN = re.compile(r"^(\d{8})-(\d{6})-(\d+)$")
LIMIT = 10
MONTHS = 6

def months_ago(today, delta):
    ym = today.year * 12 + (today.month - 1) - delta
    year, month0 = divmod(ym, 12)
    month = month0 + 1
    return date(year, month, min(today.day, calendar.monthrange(year, month)[1]))

def main(root):
    backup_root = Path(root)
    if not backup_root.is_dir() or backup_root.is_symlink():
        print("Backup retention: no valid backup directory to prune.")
        return
    cutoff = months_ago(date.today(), MONTHS)
    snapshots = []
    for path in backup_root.iterdir():
        match = PATTERN.fullmatch(path.name)
        if not match:
            continue
        mode = path.lstat().st_mode
        if not stat.S_ISDIR(mode):
            continue
        try:
            created = datetime.strptime(match.group(1), "%Y%m%d").date()
        except ValueError:
            continue
        snapshots.append((created, path))
    snapshots.sort(key=lambda x: x[1].name, reverse=True)

    retained = 0
    removed = 0
    for created, path in snapshots:
        if created < cutoff or retained >= LIMIT:
            shutil.rmtree(path)
            print("Backup retention: removed {}".format(path))
            removed += 1
        else:
            retained += 1
    print("Backup retention: kept {} snapshots, removed {}; six-month cutoff: {}".format(
        retained, removed, cutoff
    ))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: tc-wp-prune-backups.py /absolute/backup/path")
    main(sys.argv[1])
