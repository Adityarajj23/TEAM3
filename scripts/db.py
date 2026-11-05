"""Database utilities: migrate, init, integrity, backup, restore and developer-only reset.

Usage: python scripts/db.py {migrate|init|integrity|backup|restore PATH|reset}
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db import maintenance  # noqa: E402
from app.db.init_db import initialise, migrate  # noqa: E402


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "migrate":
        migrate(); print("migrations applied")
    elif cmd == "init":
        print(initialise())
    elif cmd == "integrity":
        print(maintenance.integrity_report())
    elif cmd == "backup":
        print("backup written to", maintenance.backup_database())
    elif cmd == "restore" and len(sys.argv) > 2:
        maintenance.restore_database(Path(sys.argv[2])); print("restored; restart the API")
    elif cmd == "reset":
        if input("This deletes the development database. Type 'reset' to continue: ") != "reset":
            raise SystemExit("aborted")
        maintenance.dev_reset(); print("development data removed; next start re-initialises")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
