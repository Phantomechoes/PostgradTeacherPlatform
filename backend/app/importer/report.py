from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ImportErrorItem:
    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PlannedItem:
    kind: str
    key: str
    action: Literal["create", "skip"]
    existing_inactive: bool = False


@dataclass
class ImportReport:
    mode: Literal["dry-run", "apply"] = "dry-run"
    source_file: str = ""
    manifest_file: str = ""
    planned: list[PlannedItem] = field(default_factory=list)
    errors: list[ImportErrorItem] = field(default_factory=list)
    database_written: bool = False
    committed: bool = False

    @property
    def create_count(self) -> int:
        return sum(1 for item in self.planned if item.action == "create")

    @property
    def skip_count(self) -> int:
        return sum(1 for item in self.planned if item.action == "skip")

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "source_file": self.source_file,
            "manifest_file": self.manifest_file,
            "planned": {
                "create_count": self.create_count,
                "skip_count": self.skip_count,
                "items": [
                    {
                        "kind": item.kind,
                        "key": item.key,
                        "action": item.action,
                        "existing_inactive": item.existing_inactive,
                    }
                    for item in self.planned
                ],
            },
            "errors": [
                {
                    "path": item.path,
                    "code": item.code,
                    "message": item.message,
                }
                for item in self.errors
            ],
            "created": {
                "school": _created(self.planned, "school"),
                "college": _created(self.planned, "college"),
                "major": _created(self.planned, "major"),
                "national_subject": sum(
                    1
                    for item in self.planned
                    if item.action == "create"
                    and item.kind == "exam_subject"
                    and item.key.startswith("national/")
                ),
                "school_subject": sum(
                    1
                    for item in self.planned
                    if item.action == "create"
                    and item.kind == "exam_subject"
                    and item.key.startswith("school/")
                ),
                "catalog": _created(self.planned, "catalog"),
            },
            "skipped": {
                "catalog": sum(
                    1
                    for item in self.planned
                    if item.action == "skip" and item.kind == "catalog"
                ),
            },
            "database_written": self.database_written,
            "committed": self.committed,
        }


def _created(planned: list[PlannedItem], kind: str) -> int:
    return sum(1 for item in planned if item.action == "create" and item.kind == kind)
