"""Make a consistent copy of the SQLite database and prune old copies.

Usage: python backup.py <db-path> <backup-dir> [--keep N]

Uses SQLite's online backup API, so it is safe to run while the bot is running
(a plain `cp` of a live database can produce a corrupt copy).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path


def backup(db_path: Path, dest_dir: Path, keep: int) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{db_path.stem}-{time.strftime('%Y%m%d-%H%M%S')}.db"

    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    for old in sorted(dest_dir.glob(f"{db_path.stem}-*.db"))[:-keep]:
        old.unlink()
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--keep", type=int, default=14, help="backups to retain")
    args = parser.parse_args()
    try:
        print(f"wrote {backup(args.db, args.dest, args.keep)}")
    except FileNotFoundError as err:
        sys.exit(str(err))


if __name__ == "__main__":
    main()
