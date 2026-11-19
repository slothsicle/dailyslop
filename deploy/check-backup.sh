#!/usr/bin/env bash
# Read-only health check for the dailyslop database backups.
#
# Usage (on the server): sudo bash /opt/dailyslop/deploy/check-backup.sh
#
# Reports: timer state, the last backup run, the backup files and their age, and whether the
# newest copy opens, passes SQLite's integrity check and holds a similar amount of data to the
# live database. Nothing is modified.
set -u

APP=/opt/dailyslop
DB=$APP/data/dailyslop.db
DIR=$APP/backups
PY=$APP/.venv/bin/python

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo (the backups belong to the dailyslop user)." >&2
  exit 1
fi

echo "== Timer =="
systemctl list-timers dailyslop-backup.timer --no-pager 2>&1
echo "enabled: $(systemctl is-enabled dailyslop-backup.timer 2>&1)"
echo "active:  $(systemctl is-active dailyslop-backup.timer 2>&1)"

echo
echo "== Last backup run =="
systemctl show dailyslop-backup.service -p Result -p ExecMainStatus \
  -p ExecMainStartTimestamp -p ExecMainExitTimestamp
echo "-- journal --"
journalctl -u dailyslop-backup --no-pager -n 10 2>&1

echo
echo "== Backup files ($DIR) =="
ls -l --time-style=long-iso "$DIR" 2>&1
echo "disk: $(du -sh "$DIR" 2>/dev/null | cut -f1) in backups, $(df -h --output=avail "$DIR" 2>/dev/null | tail -1 | tr -d ' ') free"

echo
echo "== Newest backup vs live database =="
sudo -u dailyslop "$PY" -I - "$DB" "$DIR" <<'PYEOF'
import sqlite3
import sys
import time
from pathlib import Path

live, folder = Path(sys.argv[1]), Path(sys.argv[2])
files = sorted(folder.glob("dailyslop-*.db"))
if not files:
    print("FAIL: no backup files found")
    sys.exit(1)
newest = files[-1]
age_h = (time.time() - newest.stat().st_mtime) / 3600
print(f"{len(files)} backup(s); newest: {newest.name}, {age_h:.1f}h old, {newest.stat().st_size:,} bytes")
print("OK: newest is under 26h old" if age_h < 26 else "WARN: newest is over 26h old, so the daily timer may not be running")


def open_ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def tables(con):
    names = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {n: con.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in names}


try:
    b = open_ro(newest)
    result = b.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"integrity_check: {result}")
    bt = tables(b)
    b.close()
except sqlite3.Error as err:
    print(f"FAIL: cannot read newest backup: {err}")
    sys.exit(1)

try:
    c = open_ro(live)
    lt = tables(c)
    c.close()
except sqlite3.Error as err:
    print(f"WARN: cannot read live database ({err}); skipping comparison")
    lt = None

print(f"\n{'table':<10}{'backup':>10}{'live':>10}")
for name in sorted(set(bt) | set(lt or {})):
    print(f"{name:<10}{bt.get(name, '-')!s:>10}{(lt or {}).get(name, '-')!s:>10}")
if lt is not None:
    print("\nThe live count should be equal to or a little above the backup (new scores since it ran).")
    if set(bt) != set(lt):
        print("NOTE: table sets differ; expected only if a release added a migration since the backup.")
    elif any(bt[n] > lt[n] for n in bt):
        print("WARN: a table has more rows in the backup than live; was data deleted or the db replaced?")
PYEOF
