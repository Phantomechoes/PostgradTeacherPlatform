from pathlib import Path

from sqlalchemy.orm import Session

from app.importer.load import load_document
from app.importer.preflight import preflight
from app.importer.report import ImportReport


def run_dry_run(data_path: Path, session: Session) -> ImportReport:
    report = ImportReport()
    document, _manifest = load_document(data_path, report)
    if document is None or report.errors:
        return report
    preflight(document, session, report)
    return report
