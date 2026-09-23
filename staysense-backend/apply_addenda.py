"""
Applies the schema_addendum_*.sql files to the database the app is configured
to use (app.config.DATABASE_URL), through SQLAlchemy — so it works without a
`mysql` CLI on PATH and regardless of whether MySQL runs in Docker or locally.

Usage:
    python apply_addenda.py                 # apply 2, 3, 4 (default set)
    python apply_addenda.py schema_addendum_4.sql
    python apply_addenda.py --list          # show what would run

Each statement is executed independently; "already applied" errors (duplicate
column, duplicate key) are reported and skipped so the script is safe to
re-run. Trigger blocks delimited by `DELIMITER $$ ... DELIMITER ;` are parsed
and sent one statement at a time (the driver needs no delimiter).
"""
import sys
from pathlib import Path

from app.database import engine

DEFAULT_FILES = [
    "schema_addendum_2.sql",
    "schema_addendum_3.sql",
    "schema_addendum_4.sql",
    "schema_addendum_5.sql",
    "schema_addendum_6.sql",
    "schema_addendum_7.sql",
    "schema_addendum_8.sql",
    "schema_addendum_9.sql",
    "schema_addendum_10.sql",
    "schema_addendum_11.sql",
    "schema_addendum_12.sql",
    "schema_addendum_13.sql",
    "schema_addendum_14.sql",
    "schema_addendum_15.sql",
    "schema_addendum_16.sql",
    "schema_addendum_17.sql",
    "schema_addendum_18.sql",
    "schema_addendum_19.sql",
    "schema_addendum_20.sql",
]

# errors that mean "this piece is already in place" — safe to skip on re-run
BENIGN = ("1060", "1061", "1050", "1062", "Duplicate column", "Duplicate key",
          "already exists")


def split_statements(sql: str) -> list[str]:
    """Split a .sql script into individual statements, honouring `DELIMITER`."""
    statements, buf, delimiter = [], [], ";"
    for raw_line in sql.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.upper().startswith("DELIMITER "):
            delimiter = stripped.split(None, 1)[1].strip()
            continue
        buf.append(line)
        if stripped.endswith(delimiter):
            chunk = "\n".join(buf)
            chunk = chunk[: chunk.rfind(delimiter)].strip()
            if chunk:
                statements.append(chunk)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def apply_file(path: Path) -> None:
    print(f"\n=== {path.name} ===")
    statements = split_statements(path.read_text(encoding="utf-8"))
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for i, stmt in enumerate(statements, 1):
            preview = " ".join(stmt.split())[:70]
            try:
                conn.exec_driver_sql(stmt)
                print(f"  [{i}/{len(statements)}] ok    {preview}")
            except Exception as e:  # noqa: BLE001 - want to keep going
                msg = str(e.orig if hasattr(e, "orig") else e)
                if any(b in msg for b in BENIGN):
                    print(f"  [{i}/{len(statements)}] skip  {preview}  ({msg.splitlines()[0][:80]})")
                else:
                    raise


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--list"]
    files = args or DEFAULT_FILES
    here = Path(__file__).parent

    if "--list" in sys.argv:
        for f in files:
            print(here / f)
        return

    print(f"Target DB: {engine.url.render_as_string(hide_password=True)}")
    for f in files:
        p = here / f
        if not p.exists():
            print(f"!! not found: {p}")
            sys.exit(1)
        apply_file(p)
    print("\nDone.")


if __name__ == "__main__":
    main()
