from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import master_data
from app.schemas.master_data import (
    AdmissionCatalogDetail,
    AdmissionCatalogSummary,
    AdmissionYearsRead,
    CollegeSummary,
    DirectionRead,
    ExamSubjectOptionRead,
    ExamSubjectSummary,
    ExamUnitRead,
    MajorSummary,
    Page,
    SchoolSummary,
)

FORBIDDEN_FIELDS = frozenset({"is_active", "created_at", "updated_at"})
READ_SCHEMAS = (
    SchoolSummary,
    CollegeSummary,
    MajorSummary,
    ExamSubjectSummary,
    DirectionRead,
    ExamSubjectOptionRead,
    ExamUnitRead,
    AdmissionCatalogSummary,
    AdmissionCatalogDetail,
    AdmissionYearsRead,
    Page,
)

SCHOOL = SchoolSummary(id=1, school_code="10001", name="北京交通大学")
COLLEGE = CollegeSummary(id=2, college_code="AI", name="自动化与智能学院")
MAJOR = MajorSummary(
    id=3,
    major_code="140500",
    name="智能科学与技术",
    degree_type="academic",
)


def _catalog_detail(
    *,
    directions: list[DirectionRead] | None = None,
    exam_units: list[ExamUnitRead] | None = None,
) -> AdmissionCatalogDetail:
    return AdmissionCatalogDetail(
        id=10,
        admission_year=2026,
        study_mode="full_time",
        school=SCHOOL,
        college=COLLEGE,
        major=MAJOR,
        directions=directions if directions is not None else [],
        exam_units=exam_units if exam_units is not None else [],
    )


def test_page_generic_constructs() -> None:
    page = Page[SchoolSummary](
        items=[SCHOOL],
        page=1,
        page_size=20,
        total=1,
    )
    assert page.items[0].school_code == "10001"
    assert page.page == 1
    assert page.page_size == 20
    assert page.total == 1


def test_detail_allows_empty_directions() -> None:
    detail = _catalog_detail(directions=[], exam_units=[])
    assert detail.directions == []


def test_detail_allows_empty_exam_units() -> None:
    detail = _catalog_detail(
        directions=[],
        exam_units=[],
    )
    assert detail.exam_units == []


def test_college_code_may_be_null() -> None:
    college = CollegeSummary(id=1, college_code=None, name="未编码学院")
    assert college.college_code is None


def test_national_exam_subject_school_id_is_none() -> None:
    subject = ExamSubjectSummary(
        id=1,
        subject_code="101",
        name="思想政治理论",
        school_id=None,
    )
    assert subject.school_id is None


def test_response_schemas_omit_is_active() -> None:
    for schema in READ_SCHEMAS:
        assert "is_active" not in schema.model_fields, schema.__name__


def test_response_schemas_omit_timestamps() -> None:
    for schema in READ_SCHEMAS:
        fields = set(schema.model_fields)
        assert "created_at" not in fields, schema.__name__
        assert "updated_at" not in fields, schema.__name__


def test_schema_module_has_no_write_models() -> None:
    names = [
        name
        for name, obj in vars(master_data).items()
        if isinstance(obj, type) and name.endswith(("Create", "Update", "Delete"))
    ]
    assert names == []


def test_schema_module_field_names_exclude_internal_columns() -> None:
    source = Path(master_data.__file__).read_text(encoding="utf-8")
    for field in FORBIDDEN_FIELDS:
        assert field not in source


def _catalog_summary(*, study_mode: str) -> AdmissionCatalogSummary:
    return AdmissionCatalogSummary(
        id=10,
        admission_year=2026,
        study_mode=study_mode,  # type: ignore[arg-type]
        school=SCHOOL,
        college=COLLEGE,
        major=MAJOR,
    )


def test_study_mode_accepts_full_time_and_part_time() -> None:
    for mode in ("full_time", "part_time"):
        summary = _catalog_summary(study_mode=mode)
        assert summary.study_mode == mode


def test_study_mode_rejects_night() -> None:
    with pytest.raises(ValidationError):
        _catalog_summary(study_mode="night")
