import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.importer.apply import run_apply
from app.importer.cli import main
from app.importer.engine import run_dry_run
from app.main import app
from app.models import (
    AdmissionCatalog,
    AdmissionCatalogDirection,
    AdmissionCatalogExamSubject,
    College,
    ExamSubject,
    Major,
    School,
)
from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository
from app.repositories.master_data import AdmissionCatalogRepository
from app.schemas.admin_catalog import (
    CatalogAggregatePut,
    CatalogShellCreate,
    DirectionWrite,
    ExamOptionWrite,
    ExamUnitWrite,
)
from app.services.admin_catalog import AdminCatalogService
from app.services.admin_master_data import AdminMasterDataService
from tests.conftest import (
    COLLEGE_A_ID,
    MAJOR_A_ID,
    PREFIX,
    SCHOOL_A_ID,
    SUBJECT_INACTIVE_ID,
    SUBJECT_NATIONAL_ID,
)

TABLES = (
    School,
    College,
    Major,
    ExamSubject,
    AdmissionCatalog,
    AdmissionCatalogDirection,
    AdmissionCatalogExamSubject,
)


def _counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: int(
            session.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in TABLES
    }


def _manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "dataset_id": "test",
        "data_kind": "development_seed",
        "source_type": "synthetic",
        "source_description": "pytest fixture",
        "publisher": "test",
        "retrieved_at": "2026-09-22",
        "verification_status": "approved",
    }


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    data = tmp_path / "sample.json"
    data.write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "sample.manifest.json").write_text(
        json.dumps(_manifest()),
        encoding="utf-8",
    )
    return data


def _base_doc(**overrides: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema_version": 1,
        "schools": [{"school_code": "NEW_S", "name": "New School"}],
        "colleges": [
            {
                "school_code": "NEW_S",
                "college_code": "CS",
                "name": "New College",
            }
        ],
        "majors": [
            {
                "school_code": "NEW_S",
                "major_code": "081200",
                "name": "New Major",
                "degree_type": "academic",
            }
        ],
        "exam_subjects": [
            {
                "scope": "national",
                "subject_code": "NEW_101",
                "name": "Politics",
            },
            {
                "scope": "school",
                "school_code": "NEW_S",
                "subject_code": "NEW_801",
                "name": "School Subject",
            },
        ],
        "catalogs": [
            {
                "school_code": "NEW_S",
                "college_code": "CS",
                "major_code": "081200",
                "admission_year": 2026,
                "study_mode": "full_time",
                "directions": [
                    {"direction_code": "01", "direction_name": "Dir"}
                ],
                "exam_units": [
                    {
                        "exam_unit": 1,
                        "options": [
                            {
                                "option_order": 1,
                                "subject_scope": "national",
                                "subject_code": "NEW_101",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    doc.update(overrides)
    return doc


def test_valid_json_accepted(db_session: Session, tmp_path: Path) -> None:
    path = _write(tmp_path, _base_doc())
    report = run_dry_run(path, db_session)
    assert report.ok
    assert report.create_count >= 5
    assert report.database_written is False


def test_invalid_schema_version(db_session: Session, tmp_path: Path) -> None:
    path = _write(tmp_path, _base_doc(schema_version=2))
    report = run_dry_run(path, db_session)
    assert not report.ok
    assert any(item.code == "invalid_schema" for item in report.errors)


def test_blank_business_code(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["schools"] = [{"school_code": "   ", "name": "X"}]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert not report.ok


def test_college_code_null_rejected(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["colleges"] = [
        {"school_code": "NEW_S", "college_code": None, "name": "X"}
    ]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert not report.ok


def test_invalid_degree_type(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["majors"] = [
        {
            "school_code": "NEW_S",
            "major_code": "081200",
            "name": "X",
            "degree_type": "硕士",
        }
    ]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert not report.ok


def test_invalid_study_mode(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    catalogs = doc["catalogs"]
    catalogs[0]["study_mode"] = "online"
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert not report.ok


def test_exam_unit_out_of_range(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["catalogs"][0]["exam_units"][0]["exam_unit"] = 5
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert not report.ok


def test_option_order_below_one(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["catalogs"][0]["exam_units"][0]["options"][0]["option_order"] = 0
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert not report.ok


def test_duplicate_school_in_document(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["schools"] = [
        {"school_code": "NEW_S", "name": "A"},
        {"school_code": "NEW_S", "name": "B"},
    ]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert any(item.code == "duplicate_in_document" for item in report.errors)


def test_duplicate_catalog_in_document(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    catalogs = doc["catalogs"]
    doc["catalogs"] = [catalogs[0], dict(catalogs[0])]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert any(item.code == "duplicate_in_document" for item in report.errors)


def test_duplicate_direction(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["catalogs"][0]["directions"] = [
        {"direction_code": "01", "direction_name": "A"},
        {"direction_code": "01", "direction_name": "B"},
    ]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert any(item.code == "duplicate_in_document" for item in report.errors)


def test_duplicate_option_order(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["catalogs"][0]["exam_units"][0]["options"] = [
        {
            "option_order": 1,
            "subject_scope": "national",
            "subject_code": "101",
        },
        {
            "option_order": 1,
            "subject_scope": "national",
            "subject_code": "201",
        },
    ]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert any(item.code == "duplicate_in_document" for item in report.errors)


def test_duplicate_subject_in_unit(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["exam_subjects"].append(
        {"scope": "national", "subject_code": "201", "name": "English"}
    )
    doc["catalogs"][0]["exam_units"][0]["options"] = [
        {
            "option_order": 1,
            "subject_scope": "national",
            "subject_code": "101",
        },
        {
            "option_order": 2,
            "subject_scope": "national",
            "subject_code": "101",
        },
    ]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert any(item.code == "duplicate_in_document" for item in report.errors)


def test_school_subject_missing_school_code(
    db_session: Session, tmp_path: Path
) -> None:
    doc = _base_doc()
    doc["exam_subjects"] = [
        {"scope": "school", "subject_code": "801", "name": "X"}
    ]
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert not report.ok


def test_unknown_reference(db_session: Session, tmp_path: Path) -> None:
    doc = _base_doc()
    doc["colleges"][0]["school_code"] = "MISSING"
    path = _write(tmp_path, doc)
    report = run_dry_run(path, db_session)
    assert any(item.code == "unknown_reference" for item in report.errors)


def test_cross_school_reference(seeded_session: Session, tmp_path: Path) -> None:
    doc = _base_doc(
        schools=[],
        colleges=[],
        majors=[],
        exam_subjects=[],
        catalogs=[
            {
                "school_code": f"{PREFIX}_A",
                "college_code": "A_COL",
                "major_code": f"{PREFIX}_140500",
                "admission_year": 2030,
                "study_mode": "full_time",
                "directions": [],
                "exam_units": [
                    {
                        "exam_unit": 1,
                        "options": [
                            {
                                "option_order": 1,
                                "subject_scope": "school",
                                "school_code": f"{PREFIX}_C",
                                "subject_code": f"{PREFIX}_895",
                            }
                        ],
                    }
                ],
            }
        ],
    )
    path = _write(tmp_path, doc)
    report = run_dry_run(path, seeded_session)
    assert any(item.code == "reference_scope_mismatch" for item in report.errors)


def test_existing_equivalent_skip(seeded_session: Session, tmp_path: Path) -> None:
    doc = {
        "schema_version": 1,
        "schools": [
            {
                "school_code": f"{PREFIX}_A",
                "name": f"{PREFIX}_AlphaUniversity",
            }
        ],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_dry_run(path, seeded_session)
    assert report.ok
    assert report.skip_count == 1
    assert report.create_count == 0


def test_existing_different_reject(seeded_session: Session, tmp_path: Path) -> None:
    doc = {
        "schema_version": 1,
        "schools": [
            {"school_code": f"{PREFIX}_A", "name": "Different Name"}
        ],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_dry_run(path, seeded_session)
    assert any(item.code == "conflict_existing" for item in report.errors)


def test_inactive_existing_equivalent_skip(
    seeded_session: Session, tmp_path: Path
) -> None:
    doc = {
        "schema_version": 1,
        "schools": [
            {
                "school_code": f"{PREFIX}_B",
                "name": f"{PREFIX}_BetaInactive",
            }
        ],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_dry_run(path, seeded_session)
    assert report.ok
    skipped = [item for item in report.planned if item.action == "skip"]
    assert skipped
    assert skipped[0].existing_inactive is True
    school = seeded_session.scalar(
        select(School).where(School.school_code == f"{PREFIX}_B")
    )
    assert school is not None
    assert school.is_active is False


def test_dry_run_does_not_write(db_session: Session, tmp_path: Path) -> None:
    before = _counts(db_session)
    names = {
        row.school_code: (row.name, row.is_active)
        for row in db_session.scalars(select(School)).all()
    }
    path = _write(tmp_path, _base_doc())
    report = run_dry_run(path, db_session)
    assert report.ok
    db_session.flush()
    assert _counts(db_session) == before
    after_names = {
        row.school_code: (row.name, row.is_active)
        for row in db_session.scalars(select(School)).all()
    }
    assert after_names == names


def test_repeat_dry_run_stable(db_session: Session, tmp_path: Path) -> None:
    path = _write(tmp_path, _base_doc())
    first = run_dry_run(path, db_session)
    second = run_dry_run(path, db_session)
    assert first.as_dict() == second.as_dict()


def test_cli_default_is_dry_run(tmp_path: Path) -> None:
    path = _write(tmp_path, _base_doc())
    assert main([str(path)]) == 0


def test_cli_apply_rejected(tmp_path: Path) -> None:
    doc = _base_doc()
    doc["catalogs"][0]["school_code"] = "MISSING_SCHOOL"
    path = _write(tmp_path, doc)
    assert main([str(path), "--apply"]) == 1


def _master_doc() -> dict[str, object]:
    return _base_doc(catalogs=[])


def test_apply_creates_stable_master(db_session: Session, tmp_path: Path) -> None:
    path = _write(tmp_path, _master_doc())
    before = _counts(db_session)
    report = run_apply(path, db_session)
    assert report.ok
    assert report.mode == "apply"
    assert report.database_written is True
    assert report.create_count == 5
    school = db_session.scalar(select(School).where(School.school_code == "NEW_S"))
    assert school is not None
    assert school.name == "New School"
    assert school.is_active is True
    college = db_session.scalar(
        select(College).where(
            College.school_id == school.id,
            College.college_code == "CS",
        )
    )
    assert college is not None
    major = db_session.scalar(
        select(Major).where(
            Major.school_id == school.id,
            Major.major_code == "081200",
        )
    )
    assert major is not None
    assert major.degree_type == "academic"
    national = db_session.scalar(
        select(ExamSubject).where(
            ExamSubject.school_id.is_(None),
            ExamSubject.subject_code == "NEW_101",
        )
    )
    assert national is not None
    school_subject = db_session.scalar(
        select(ExamSubject).where(
            ExamSubject.school_id == school.id,
            ExamSubject.subject_code == "NEW_801",
        )
    )
    assert school_subject is not None
    assert college.is_active is True
    assert major.is_active is True
    assert national.is_active is True
    assert school_subject.is_active is True
    payload = report.as_dict()
    assert payload["created"] == {
        "school": 1,
        "college": 1,
        "major": 1,
        "national_subject": 1,
        "school_subject": 1,
        "catalog": 0,
    }
    after = _counts(db_session)
    assert after["schools"] == before["schools"] + 1
    assert after["colleges"] == before["colleges"] + 1
    assert after["majors"] == before["majors"] + 1
    assert after["exam_subjects"] == before["exam_subjects"] + 2
    assert after["admission_catalogs"] == before["admission_catalogs"]


def test_second_apply_all_skip(db_session: Session, tmp_path: Path) -> None:
    path = _write(tmp_path, _master_doc())
    first = run_apply(path, db_session)
    assert first.ok
    counts = _counts(db_session)
    second = run_apply(path, db_session)
    assert second.ok
    assert second.create_count == 0
    assert second.skip_count == 5
    assert _counts(db_session) == counts


def test_apply_conflict_writes_nothing(seeded_session: Session, tmp_path: Path) -> None:
    before = _counts(seeded_session)
    doc = {
        "schema_version": 1,
        "schools": [{"school_code": f"{PREFIX}_A", "name": "Different Name"}],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert report.database_written is False
    assert _counts(seeded_session) == before
    school = seeded_session.scalar(
        select(School).where(School.school_code == f"{PREFIX}_A")
    )
    assert school is not None
    assert school.name == f"{PREFIX}_AlphaUniversity"


def test_apply_inactive_equivalent_does_not_reactivate(
    seeded_session: Session, tmp_path: Path
) -> None:
    doc = {
        "schema_version": 1,
        "schools": [
            {
                "school_code": f"{PREFIX}_B",
                "name": f"{PREFIX}_BetaInactive",
            }
        ],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_apply(path, seeded_session)
    assert report.ok
    assert report.skip_count == 1
    school = seeded_session.scalar(
        select(School).where(School.school_code == f"{PREFIX}_B")
    )
    assert school is not None
    assert school.is_active is False


def _catalog_by_offering(
    session: Session,
    school_code: str,
    college_code: str,
    major_code: str,
    admission_year: int,
    study_mode: str,
) -> AdmissionCatalog | None:
    schools = AdminSchoolRepository(session)
    school = schools.get_school_by_code(school_code)
    if school is None:
        return None
    college = schools.get_college_by_school_and_code(school.id, college_code)
    major = schools.get_major_by_school_and_code(school.id, major_code)
    if college is None or major is None:
        return None
    return AdminCatalogRepository(session).get_catalog_by_offering(
        school_id=school.id,
        college_id=college.id,
        major_id=major.id,
        admission_year=admission_year,
        study_mode=study_mode,
    )


def _child_ids(session: Session, catalog_id: int) -> tuple[list[int], list[int]]:
    directions = list(
        session.scalars(
            select(AdmissionCatalogDirection.id).where(
                AdmissionCatalogDirection.admission_catalog_id == catalog_id
            )
        )
    )
    options = list(
        session.scalars(
            select(AdmissionCatalogExamSubject.id).where(
                AdmissionCatalogExamSubject.admission_catalog_id == catalog_id
            )
        )
    )
    return directions, options


def _child_counts(session: Session, catalog_id: int) -> tuple[int, int]:
    directions, options = _child_ids(session, catalog_id)
    return len(directions), len(options)


def _catalog_service(session: Session) -> AdminCatalogService:
    return AdminCatalogService(
        AdminCatalogRepository(session),
        AdminSchoolRepository(session),
    )


def test_apply_creates_inactive_catalog(db_session: Session, tmp_path: Path) -> None:
    before = _counts(db_session)
    path = _write(tmp_path, _base_doc())
    report = run_apply(path, db_session)
    assert report.ok
    assert report.database_written is True
    assert report.as_dict()["created"]["catalog"] == 1
    catalog = _catalog_by_offering(
        db_session, "NEW_S", "CS", "081200", 2026, "full_time"
    )
    assert catalog is not None
    assert catalog.is_active is False
    assert _child_counts(db_session, catalog.id) == (1, 1)
    after = _counts(db_session)
    assert after["admission_catalogs"] == before["admission_catalogs"] + 1
    assert after["admission_catalog_directions"] == (
        before["admission_catalog_directions"] + 1
    )
    assert after["admission_catalog_exam_subjects"] == (
        before["admission_catalog_exam_subjects"] + 1
    )
    assert AdmissionCatalogRepository(db_session).get_catalog(catalog.id) is None


def test_apply_rollback_after_flush(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whole-file transaction: School/College/Major/national subject already
    flushed, then school-subject create is injected to fail; rollback must
    remove every flushed row.
    """
    path = _write(tmp_path, _master_doc())
    before = _counts(db_session)

    def boom(self: object, school_id: int, data: object) -> None:
        raise RuntimeError("injected failure after prior inserts")

    monkeypatch.setattr(
        AdminMasterDataService,
        "create_school_exam_subject",
        boom,
    )
    with pytest.raises(RuntimeError, match="injected failure"):
        run_apply(path, db_session)
    db_session.rollback()
    assert _counts(db_session) == before
    assert db_session.scalar(select(School).where(School.school_code == "NEW_S")) is None
    assert db_session.scalar(
        select(ExamSubject).where(
            ExamSubject.school_id.is_(None),
            ExamSubject.subject_code == "NEW_101",
        )
    ) is None


def test_seed_document_dry_run(db_session: Session) -> None:
    seed = Path(__file__).resolve().parents[1] / "data" / "seeds" / "devseed.json"
    before = _counts(db_session)
    report = run_dry_run(seed, db_session)
    assert report.ok
    assert report.database_written is False
    assert report.committed is False
    assert report.create_count == 6
    assert _counts(db_session) == before


def test_existing_catalog_equivalent_skip(
    seeded_session: Session, tmp_path: Path
) -> None:
    doc = {
        "schema_version": 1,
        "schools": [],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [
            {
                "school_code": f"{PREFIX}_A",
                "college_code": "A_COL",
                "major_code": f"{PREFIX}_140500",
                "admission_year": 2028,
                "study_mode": "full_time",
                "directions": [],
                "exam_units": [],
            }
        ],
    }
    path = _write(tmp_path, doc)
    report = run_dry_run(path, seeded_session)
    assert report.ok
    skipped = [item for item in report.planned if item.kind == "catalog"]
    assert skipped
    assert skipped[0].action == "skip"
    assert skipped[0].existing_inactive is True


def test_existing_catalog_different_reject(
    seeded_session: Session, tmp_path: Path
) -> None:
    doc = {
        "schema_version": 1,
        "schools": [],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [
            {
                "school_code": f"{PREFIX}_A",
                "college_code": "A_COL",
                "major_code": f"{PREFIX}_140500",
                "admission_year": 2027,
                "study_mode": "full_time",
                "directions": [],
                "exam_units": [],
            }
        ],
    }
    path = _write(tmp_path, doc)
    report = run_dry_run(path, seeded_session)
    assert any(item.code == "conflict_existing" for item in report.errors)


def test_apply_major_conflict_writes_nothing(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    doc = {
        "schema_version": 1,
        "schools": [{"school_code": "NEW_S", "name": "New School"}],
        "colleges": [],
        "majors": [
            {
                "school_code": f"{PREFIX}_A",
                "major_code": f"{PREFIX}_140500",
                "name": f"{PREFIX}_MAJOR_A",
                "degree_type": "professional",
            }
        ],
        "exam_subjects": [],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "conflict_existing" for item in report.errors)
    assert report.database_written is False
    assert seeded_session.scalar(
        select(School).where(School.school_code == "NEW_S")
    ) is None
    parent = seeded_session.scalar(
        select(School).where(School.school_code == f"{PREFIX}_A")
    )
    assert parent is not None
    major = seeded_session.scalar(
        select(Major).where(
            Major.school_id == parent.id,
            Major.major_code == f"{PREFIX}_140500",
        )
    )
    assert major is not None
    assert major.degree_type == "academic"
    assert _counts(seeded_session) == before


def test_apply_subject_conflict_writes_nothing(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    doc = {
        "schema_version": 1,
        "schools": [{"school_code": "NEW_S", "name": "New School"}],
        "colleges": [],
        "majors": [],
        "exam_subjects": [
            {
                "scope": "national",
                "subject_code": f"{PREFIX}_101",
                "name": "Different National Name",
            }
        ],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "conflict_existing" for item in report.errors)
    assert report.database_written is False
    assert seeded_session.scalar(
        select(School).where(School.school_code == "NEW_S")
    ) is None
    subject = seeded_session.scalar(
        select(ExamSubject).where(
            ExamSubject.school_id.is_(None),
            ExamSubject.subject_code == f"{PREFIX}_101",
        )
    )
    assert subject is not None
    assert subject.name == f"{PREFIX}_NATIONAL"
    assert _counts(seeded_session) == before


def test_apply_inactive_school_new_child_parent_inactive(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    doc = {
        "schema_version": 1,
        "schools": [],
        "colleges": [
            {
                "school_code": f"{PREFIX}_B",
                "college_code": "NEW_COL",
                "name": "Should Not Persist",
            }
        ],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [],
    }
    path = _write(tmp_path, doc)
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "parent_inactive" for item in report.errors)
    assert report.database_written is False
    assert seeded_session.scalar(
        select(College).where(College.college_code == "NEW_COL")
    ) is None
    school = seeded_session.scalar(
        select(School).where(School.school_code == f"{PREFIX}_B")
    )
    assert school is not None
    assert school.is_active is False
    assert _counts(seeded_session) == before


def test_apply_nonsynthetic_manifest_rejected(
    db_session: Session, tmp_path: Path
) -> None:
    before = _counts(db_session)
    data = tmp_path / "sample.json"
    data.write_text(json.dumps(_master_doc()), encoding="utf-8")
    (tmp_path / "sample.manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_id": "test",
                "data_kind": "development_seed",
                "source_type": "official",
                "source_description": "not synthetic",
                "publisher": "test",
                "retrieved_at": "2026-09-22",
                "verification_status": "approved",
            }
        ),
        encoding="utf-8",
    )
    report = run_apply(data, db_session)
    assert not report.ok
    assert report.database_written is False
    assert report.committed is False
    assert db_session.scalar(select(School).where(School.school_code == "NEW_S")) is None
    assert _counts(db_session) == before


def test_apply_retry_succeeds_after_rollback(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, _master_doc())
    before = _counts(db_session)

    def boom(self: object, school_id: int, data: object) -> None:
        raise RuntimeError("injected failure after prior inserts")

    monkeypatch.setattr(
        AdminMasterDataService,
        "create_school_exam_subject",
        boom,
    )
    with pytest.raises(RuntimeError, match="injected failure"):
        run_apply(path, db_session)
    db_session.rollback()
    assert _counts(db_session) == before
    monkeypatch.undo()
    report = run_apply(path, db_session)
    assert report.ok
    assert report.database_written is True
    school = db_session.scalar(select(School).where(School.school_code == "NEW_S"))
    assert school is not None
    assert school.is_active is True


def test_seed_document_apply_creates_catalog(db_session: Session) -> None:
    seed = Path(__file__).resolve().parents[1] / "data" / "seeds" / "devseed.json"
    first = run_apply(seed, db_session)
    assert first.ok
    assert first.create_count == 6
    catalog = _catalog_by_offering(
        db_session, "DEVSEED_S1", "DEVSEED_CS", "DEVSEED_081200", 2026, "full_time"
    )
    assert catalog is not None
    assert catalog.is_active is False
    assert _child_counts(db_session, catalog.id) == (1, 3)
    children = _child_ids(db_session, catalog.id)
    counts = _counts(db_session)
    second = run_apply(seed, db_session)
    assert second.ok
    assert second.create_count == 0
    assert second.skip_count == 6
    assert second.as_dict()["skipped"]["catalog"] == 1
    again = _catalog_by_offering(
        db_session, "DEVSEED_S1", "DEVSEED_CS", "DEVSEED_081200", 2026, "full_time"
    )
    assert again is not None
    assert again.id == catalog.id
    assert again.is_active is False
    assert _child_ids(db_session, again.id) == children
    assert _counts(db_session) == counts


def _prefix_catalog_doc(
    *,
    admission_year: int,
    directions: list[dict[str, object]] | None = None,
    exam_units: list[dict[str, object]] | None = None,
    extra_schools: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "schools": extra_schools or [],
        "colleges": [],
        "majors": [],
        "exam_subjects": [],
        "catalogs": [
            {
                "school_code": f"{PREFIX}_A",
                "college_code": "A_COL",
                "major_code": f"{PREFIX}_140500",
                "admission_year": admission_year,
                "study_mode": "full_time",
                "directions": directions if directions is not None else [],
                "exam_units": exam_units if exam_units is not None else [],
            }
        ],
    }


def test_second_apply_catalog_idempotent(db_session: Session, tmp_path: Path) -> None:
    path = _write(tmp_path, _base_doc())
    first = run_apply(path, db_session)
    assert first.ok
    catalog = _catalog_by_offering(
        db_session, "NEW_S", "CS", "081200", 2026, "full_time"
    )
    assert catalog is not None
    children = _child_ids(db_session, catalog.id)
    counts = _counts(db_session)
    second = run_apply(path, db_session)
    assert second.ok
    assert second.create_count == 0
    assert second.as_dict()["skipped"]["catalog"] == 1
    again = _catalog_by_offering(
        db_session, "NEW_S", "CS", "081200", 2026, "full_time"
    )
    assert again is not None
    assert again.id == catalog.id
    assert again.is_active is False
    assert _child_ids(db_session, again.id) == children
    assert _counts(db_session) == counts


def test_apply_equivalent_inactive_catalog_skip(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    catalog = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2028,
        "full_time",
    )
    assert catalog is not None
    catalog_id = catalog.id
    children = _child_ids(seeded_session, catalog_id)
    path = _write(tmp_path, _prefix_catalog_doc(admission_year=2028))
    report = run_apply(path, seeded_session)
    assert report.ok
    assert report.as_dict()["skipped"]["catalog"] == 1
    again = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2028,
        "full_time",
    )
    assert again is not None
    assert again.id == catalog_id
    assert again.is_active is False
    assert _child_ids(seeded_session, catalog_id) == children
    assert _counts(seeded_session) == before


def test_apply_equivalent_active_catalog_skip(
    seeded_session: Session, tmp_path: Path
) -> None:
    catalog = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2026,
        "full_time",
    )
    assert catalog is not None
    assert catalog.is_active is True
    catalog_id = catalog.id
    path = _write(tmp_path, _prefix_catalog_doc(admission_year=2026))
    report = run_apply(path, seeded_session)
    assert report.ok
    assert report.as_dict()["skipped"]["catalog"] == 1
    again = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2026,
        "full_time",
    )
    assert again is not None
    assert again.id == catalog_id
    assert again.is_active is True


def test_apply_active_equivalent_with_inactive_subject_skips(
    seeded_session: Session, tmp_path: Path
) -> None:
    service = _catalog_service(seeded_session)
    created = service.create_shell(
        CatalogShellCreate(
            school_id=SCHOOL_A_ID,
            college_id=COLLEGE_A_ID,
            major_id=MAJOR_A_ID,
            admission_year=2037,
            study_mode="full_time",
        )
    )
    service.replace_aggregate(
        created.id,
        CatalogAggregatePut(
            school_id=SCHOOL_A_ID,
            college_id=COLLEGE_A_ID,
            major_id=MAJOR_A_ID,
            admission_year=2037,
            study_mode="full_time",
            directions=[
                DirectionWrite(direction_code="01", direction_name="Keep")
            ],
            exam_units=[
                ExamUnitWrite(
                    exam_unit=1,
                    options=[
                        ExamOptionWrite(
                            option_order=1,
                            exam_subject_id=SUBJECT_NATIONAL_ID,
                        )
                    ],
                )
            ],
        ),
    )
    service.set_status(created.id, True)
    AdminMasterDataService(AdminSchoolRepository(seeded_session)).set_exam_subject_status(
        SUBJECT_NATIONAL_ID,
        False,
    )
    children = _child_ids(seeded_session, created.id)
    path = _write(
        tmp_path,
        _prefix_catalog_doc(
            admission_year=2037,
            directions=[{"direction_code": "01", "direction_name": "Keep"}],
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {
                            "option_order": 1,
                            "subject_scope": "national",
                            "subject_code": f"{PREFIX}_101",
                        }
                    ],
                }
            ],
        ),
    )
    report = run_apply(path, seeded_session)
    assert report.ok
    assert report.as_dict()["skipped"]["catalog"] == 1
    again = seeded_session.get(AdmissionCatalog, created.id)
    assert again is not None
    assert again.is_active is True
    assert _child_ids(seeded_session, created.id) == children
    subject = seeded_session.get(ExamSubject, SUBJECT_NATIONAL_ID)
    assert subject is not None
    assert subject.is_active is False


def test_apply_direction_conflict_writes_nothing(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    path = _write(
        tmp_path,
        _prefix_catalog_doc(
            admission_year=2027,
            directions=[{"direction_code": "01", "direction_name": "Different"}],
            extra_schools=[{"school_code": "NEW_S", "name": "New School"}],
        ),
    )
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "conflict_existing" for item in report.errors)
    assert report.database_written is False
    assert seeded_session.scalar(
        select(School).where(School.school_code == "NEW_S")
    ) is None
    catalog = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2027,
        "full_time",
    )
    assert catalog is not None
    assert catalog.is_active is True
    assert _child_counts(seeded_session, catalog.id) == (2, 4)
    assert _counts(seeded_session) == before


def test_apply_exam_option_conflict_writes_nothing(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    path = _write(
        tmp_path,
        _prefix_catalog_doc(
            admission_year=2027,
            directions=[
                {"direction_code": "01", "direction_name": f"{PREFIX}_DIR_01"},
                {"direction_code": "02", "direction_name": f"{PREFIX}_DIR_02"},
            ],
            exam_units=[],
        ),
    )
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "conflict_existing" for item in report.errors)
    assert report.database_written is False
    catalog = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2027,
        "full_time",
    )
    assert catalog is not None
    assert _child_counts(seeded_session, catalog.id) == (2, 4)
    assert _counts(seeded_session) == before


def test_apply_invalid_subject_reference_writes_nothing(
    db_session: Session, tmp_path: Path
) -> None:
    before = _counts(db_session)
    doc = _base_doc()
    doc["catalogs"][0]["exam_units"][0]["options"][0]["subject_code"] = "MISSING"
    path = _write(tmp_path, doc)
    report = run_apply(path, db_session)
    assert not report.ok
    assert any(item.code == "unknown_reference" for item in report.errors)
    assert report.database_written is False
    assert db_session.scalar(select(School).where(School.school_code == "NEW_S")) is None
    assert _counts(db_session) == before


def test_apply_invalid_college_reference_writes_nothing(
    db_session: Session, tmp_path: Path
) -> None:
    before = _counts(db_session)
    doc = _base_doc()
    doc["catalogs"][0]["college_code"] = "MISSING_COL"
    path = _write(tmp_path, doc)
    report = run_apply(path, db_session)
    assert not report.ok
    assert any(item.code == "unknown_reference" for item in report.errors)
    assert db_session.scalar(select(School).where(School.school_code == "NEW_S")) is None
    assert _counts(db_session) == before


def test_apply_scope_mismatch_foreign_subject(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    path = _write(
        tmp_path,
        _prefix_catalog_doc(
            admission_year=2033,
            extra_schools=[{"school_code": "NEW_S", "name": "New School"}],
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {
                            "option_order": 1,
                            "subject_scope": "school",
                            "school_code": f"{PREFIX}_C",
                            "subject_code": f"{PREFIX}_895",
                        }
                    ],
                }
            ],
        ),
    )
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "reference_scope_mismatch" for item in report.errors)
    assert seeded_session.scalar(
        select(School).where(School.school_code == "NEW_S")
    ) is None
    assert _counts(seeded_session) == before


def test_apply_foreign_college_code_unknown_reference(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "schools": [{"school_code": "NEW_S", "name": "New School"}],
            "colleges": [],
            "majors": [],
            "exam_subjects": [],
            "catalogs": [
                {
                    "school_code": f"{PREFIX}_A",
                    "college_code": "C_COL",
                    "major_code": f"{PREFIX}_140500",
                    "admission_year": 2033,
                    "study_mode": "full_time",
                    "directions": [],
                    "exam_units": [],
                }
            ],
        },
    )
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "unknown_reference" for item in report.errors)
    assert seeded_session.scalar(
        select(School).where(School.school_code == "NEW_S")
    ) is None
    assert _counts(seeded_session) == before


def test_apply_inactive_college_reference_rejected(
    seeded_session: Session, tmp_path: Path
) -> None:
    before = _counts(seeded_session)
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "schools": [],
            "colleges": [],
            "majors": [],
            "exam_subjects": [],
            "catalogs": [
                {
                    "school_code": f"{PREFIX}_A",
                    "college_code": "Z_COL",
                    "major_code": f"{PREFIX}_140500",
                    "admission_year": 2040,
                    "study_mode": "full_time",
                    "directions": [],
                    "exam_units": [],
                }
            ],
        },
    )
    report = run_apply(path, seeded_session)
    assert not report.ok
    assert any(item.code == "inactive_reference" for item in report.errors)
    assert _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "Z_COL",
        f"{PREFIX}_140500",
        2040,
        "full_time",
    ) is None
    assert _counts(seeded_session) == before


def test_apply_inactive_subject_on_new_inactive_catalog(
    seeded_session: Session, tmp_path: Path
) -> None:
    path = _write(
        tmp_path,
        _prefix_catalog_doc(
            admission_year=2041,
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {
                            "option_order": 1,
                            "subject_scope": "school",
                            "school_code": f"{PREFIX}_A",
                            "subject_code": f"{PREFIX}_999",
                        }
                    ],
                }
            ],
        ),
    )
    report = run_apply(path, seeded_session)
    assert report.ok
    catalog = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2041,
        "full_time",
    )
    assert catalog is not None
    assert catalog.is_active is False
    assert _child_counts(seeded_session, catalog.id) == (0, 1)
    subject = seeded_session.get(ExamSubject, SUBJECT_INACTIVE_ID)
    assert subject is not None
    assert subject.is_active is False


def test_apply_empty_aggregate(seeded_session: Session, tmp_path: Path) -> None:
    path = _write(tmp_path, _prefix_catalog_doc(admission_year=2038))
    report = run_apply(path, seeded_session)
    assert report.ok
    catalog = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2038,
        "full_time",
    )
    assert catalog is not None
    assert catalog.is_active is False
    assert _child_counts(seeded_session, catalog.id) == (0, 0)


def test_apply_or_options_noncontiguous_order(
    seeded_session: Session, tmp_path: Path
) -> None:
    path = _write(
        tmp_path,
        _prefix_catalog_doc(
            admission_year=2039,
            directions=[{"direction_code": "01", "direction_name": "Dir"}],
            exam_units=[
                {
                    "exam_unit": 2,
                    "options": [
                        {
                            "option_order": 1,
                            "subject_scope": "national",
                            "subject_code": f"{PREFIX}_101",
                        },
                        {
                            "option_order": 3,
                            "subject_scope": "school",
                            "school_code": f"{PREFIX}_A",
                            "subject_code": f"{PREFIX}_895",
                        },
                    ],
                }
            ],
        ),
    )
    report = run_apply(path, seeded_session)
    assert report.ok
    catalog = _catalog_by_offering(
        seeded_session,
        f"{PREFIX}_A",
        "A_COL",
        f"{PREFIX}_140500",
        2039,
        "full_time",
    )
    assert catalog is not None
    assert catalog.is_active is False
    assert _child_counts(seeded_session, catalog.id) == (1, 2)
    orders = list(
        seeded_session.scalars(
            select(AdmissionCatalogExamSubject.option_order)
            .where(AdmissionCatalogExamSubject.admission_catalog_id == catalog.id)
            .order_by(AdmissionCatalogExamSubject.option_order)
        )
    )
    assert orders == [1, 3]


def test_apply_rollback_after_catalog_child_flush(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catalog A shell+children and Catalog B shell are flushed, then Catalog B
    replace_aggregate is injected to fail; rollback must remove every new row.
    """
    doc = _base_doc()
    second = dict(doc["catalogs"][0])
    second["admission_year"] = 2027
    second["directions"] = []
    second["exam_units"] = []
    doc["catalogs"] = [doc["catalogs"][0], second]
    path = _write(tmp_path, doc)
    before = _counts(db_session)
    calls = {"n": 0}
    original = AdminCatalogService.replace_aggregate

    def boom(self: object, catalog_id: int, data: object) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            return original(self, catalog_id, data)
        raise RuntimeError("injected catalog B aggregate failure")

    monkeypatch.setattr(AdminCatalogService, "replace_aggregate", boom)
    with pytest.raises(RuntimeError, match="injected catalog B aggregate failure"):
        run_apply(path, db_session)
    db_session.rollback()
    assert calls["n"] == 2
    assert _counts(db_session) == before
    assert db_session.scalar(select(School).where(School.school_code == "NEW_S")) is None
    assert _catalog_by_offering(
        db_session, "NEW_S", "CS", "081200", 2026, "full_time"
    ) is None
    assert _catalog_by_offering(
        db_session, "NEW_S", "CS", "081200", 2027, "full_time"
    ) is None


def test_public_api_hides_imported_inactive_catalog(
    db_session: Session, tmp_path: Path
) -> None:
    path = _write(tmp_path, _base_doc())
    report = run_apply(path, db_session)
    assert report.ok
    catalog = _catalog_by_offering(
        db_session, "NEW_S", "CS", "081200", 2026, "full_time"
    )
    assert catalog is not None

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        client = TestClient(app)
        public = client.get(f"/api/v1/admission-catalogs/{catalog.id}")
        assert public.status_code == 404
        admin = client.get(f"/api/v1/admin/admission-catalogs/{catalog.id}")
        assert admin.status_code == 200
        body = admin.json()
        assert body["is_active"] is False
        assert len(body["directions"]) == 1
        assert len(body["exam_units"]) == 1
    finally:
        app.dependency_overrides.clear()
