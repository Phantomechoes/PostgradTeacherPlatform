import json
from pathlib import Path

from pydantic import ValidationError

from app.importer.report import ImportErrorItem, ImportReport
from app.importer.schemas import ImportDocument, ImportManifest


def json_pointer(loc: tuple[object, ...]) -> str:
    parts = [""]
    for item in loc:
        parts.append(str(item))
    return "/".join(parts) if loc else "/"


def validation_errors(error: ValidationError, prefix: str = "") -> list[ImportErrorItem]:
    items: list[ImportErrorItem] = []
    for err in error.errors():
        pointer = json_pointer(err["loc"])
        if prefix:
            pointer = prefix.rstrip("/") + pointer
        items.append(
            ImportErrorItem(
                path=pointer,
                code="invalid_schema",
                message=err["msg"],
            )
        )
    return items


def load_json(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def sidecar_path(data_path: Path) -> Path:
    return data_path.with_name(f"{data_path.stem}.manifest{data_path.suffix}")


def load_document(
    data_path: Path,
    report: ImportReport,
) -> tuple[ImportDocument | None, ImportManifest | None]:
    report.source_file = str(data_path)
    manifest_file = sidecar_path(data_path)
    report.manifest_file = str(manifest_file)
    document: ImportDocument | None = None
    manifest: ImportManifest | None = None
    try:
        raw = load_json(data_path)
        document = ImportDocument.model_validate(raw)
    except FileNotFoundError:
        report.errors.append(
            ImportErrorItem(
                path="/",
                code="missing_file",
                message=f"data file not found: {data_path}",
            )
        )
    except json.JSONDecodeError as exc:
        report.errors.append(
            ImportErrorItem(
                path="/",
                code="invalid_json",
                message=str(exc),
            )
        )
    except ValidationError as exc:
        report.errors.extend(validation_errors(exc))
    if not manifest_file.is_file():
        report.errors.append(
            ImportErrorItem(
                path="/",
                code="missing_manifest",
                message=f"manifest not found: {manifest_file}",
            )
        )
        return document, manifest
    try:
        manifest = ImportManifest.model_validate(load_json(manifest_file))
    except json.JSONDecodeError as exc:
        report.errors.append(
            ImportErrorItem(
                path="/",
                code="invalid_json",
                message=f"manifest: {exc}",
            )
        )
    except ValidationError as exc:
        report.errors.extend(validation_errors(exc, prefix="/manifest"))
    return document, manifest
