from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.importer.apply import run_apply
from app.importer.engine import run_dry_run
from app.importer.report import ImportReport

DRY_BANNER = "DRY RUN\nNO DATABASE WRITES"
APPLY_OK_BANNER = "APPLY COMPLETE\nDATABASE WRITTEN"
APPLY_REJECTED_BANNER = "APPLY REJECTED\nROLLED BACK"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.importer",
        description="Master data import. Default is dry-run.",
    )
    parser.add_argument("data_json", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply stable master data and catalogs in one transaction. "
            "New catalogs stay inactive and are not published."
        ),
    )
    return parser


def print_report(report: ImportReport, banner: str) -> None:
    print(banner)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = SessionLocal()
    try:
        if args.apply:
            report = run_apply(args.data_json, session)
            if report.ok:
                session.commit()
                report.database_written = True
                report.committed = True
                print_report(report, APPLY_OK_BANNER)
                return 0
            session.rollback()
            report.database_written = False
            report.committed = False
            print_report(report, APPLY_REJECTED_BANNER)
            return 1
        report = run_dry_run(args.data_json, session)
        session.rollback()
        print_report(report, DRY_BANNER)
        return 0 if report.ok else 1
    except Exception:
        session.rollback()
        print(APPLY_REJECTED_BANNER)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
