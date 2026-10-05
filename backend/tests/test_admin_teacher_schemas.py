import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.admin_teacher import (
    AdmissionRecordAdminRead,
    AdmissionRecordCreate,
    AdmissionRecordUpdate,
    AvailabilityUpdate,
    TeacherAdminDetail,
    TeacherAdminSummary,
    TeacherCreate,
    TeacherUpdate,
    TeachSubjectsPut,
    VerificationUpdate,
)

FORBIDDEN_TEACHER_WRITE_FIELDS = frozenset(
    {
        "id",
        "is_active",
        "availability_status",
        "verification_status",
        "created_at",
        "updated_at",
        "phone",
        "mobile",
        "wechat",
        "qq",
        "email",
        "address",
    }
)
FORBIDDEN_ADMISSION_WRITE_FIELDS = frozenset(
    {"id", "teacher_profile_id", "is_active", "created_at", "updated_at"}
)

INACTIVE_SCHOOL = {
    "id": 1,
    "school_code": "ZZ_S202_SCH",
    "name": "ZZ_S202 School",
    "is_active": False,
}
INACTIVE_COLLEGE = {
    "id": 2,
    "school_id": 1,
    "college_code": "ZZ_COL",
    "name": "ZZ_S202 College",
    "is_active": False,
}
INACTIVE_MAJOR = {
    "id": 3,
    "school_id": 1,
    "major_code": "ZZ140500",
    "name": "ZZ_S202 Major",
    "degree_type": "academic",
    "is_active": False,
}
INACTIVE_SUBJECT = {
    "id": 11,
    "school_id": None,
    "subject_code": "ZZ101",
    "name": "ZZ_S202 National Subject",
    "is_active": False,
}


def _admission_create(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "school_id": 1,
        "college_id": 2,
        "major_id": 3,
        "admission_year": 2025,
        "study_mode": "full_time",
    }
    body.update(overrides)
    return body


def _admission_read(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": 20,
        "teacher_profile_id": 9,
        "school": INACTIVE_SCHOOL,
        "college": INACTIVE_COLLEGE,
        "major": INACTIVE_MAJOR,
        "admission_year": 2025,
        "study_mode": "full_time",
        "admission_catalog_id": None,
        "initial_total": Decimal("321.50"),
        "retest_total": Decimal("85.50"),
        "final_total": Decimal("410.25"),
        "is_active": False,
    }
    body.update(overrides)
    return body


def test_teacher_create_accepts_name_and_bio() -> None:
    created = TeacherCreate.model_validate(
        {"display_name": "ZZ_S202_T1", "bio": "ZZ_S202 synthetic bio"}
    )
    assert created.display_name == "ZZ_S202_T1"
    assert created.bio == "ZZ_S202 synthetic bio"


def test_teacher_create_bio_omitted_or_null() -> None:
    omitted = TeacherCreate.model_validate({"display_name": "ZZ_S202_T1"})
    assert omitted.bio is None
    assert "bio" not in omitted.model_fields_set
    explicit_null = TeacherCreate.model_validate(
        {"display_name": "ZZ_S202_T1", "bio": None}
    )
    assert explicit_null.bio is None
    assert "bio" in explicit_null.model_fields_set


def test_teacher_create_rejects_blank_or_null_name() -> None:
    with pytest.raises(ValidationError):
        TeacherCreate.model_validate({"display_name": ""})
    with pytest.raises(ValidationError):
        TeacherCreate.model_validate({"display_name": "   "})
    with pytest.raises(ValidationError):
        TeacherCreate.model_validate({"display_name": None})
    with pytest.raises(ValidationError):
        TeacherCreate.model_validate({})


def test_teacher_create_rejects_blank_bio() -> None:
    with pytest.raises(ValidationError):
        TeacherCreate.model_validate({"display_name": "ZZ_S202_T1", "bio": ""})
    with pytest.raises(ValidationError):
        TeacherCreate.model_validate({"display_name": "ZZ_S202_T1", "bio": "  "})


def test_teacher_create_forbids_status_contact_and_extra() -> None:
    names = set(TeacherCreate.model_fields)
    assert FORBIDDEN_TEACHER_WRITE_FIELDS & names == set()
    for extra in (
        {"is_active": True},
        {"verification_status": "verified"},
        {"availability_status": "available"},
        {"phone": "13800000000"},
        {"wechat": "zz_wx"},
        {"email": "zz@example.com"},
        {"id": 1},
        {"created_at": "2026-01-01T00:00:00Z"},
    ):
        body = {"display_name": "ZZ_S202_T1", **extra}
        with pytest.raises(ValidationError):
            TeacherCreate.model_validate(body)


def test_teacher_update_partial_and_exclude_unset() -> None:
    name_only = TeacherUpdate.model_validate({"display_name": "ZZ_S202_T2"})
    assert name_only.model_dump(exclude_unset=True) == {"display_name": "ZZ_S202_T2"}
    bio_only = TeacherUpdate.model_validate({"bio": "ZZ_S202 updated"})
    assert bio_only.model_dump(exclude_unset=True) == {"bio": "ZZ_S202 updated"}
    cleared = TeacherUpdate.model_validate({"bio": None})
    assert "bio" in cleared.model_fields_set
    assert "display_name" not in cleared.model_fields_set
    assert cleared.model_dump(exclude_unset=True) == {"bio": None}
    omitted = TeacherUpdate.model_validate({})
    assert omitted.model_fields_set == set()
    assert omitted.model_dump(exclude_unset=True) == {}


def test_teacher_update_rejects_null_or_blank_display_name() -> None:
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"display_name": None})
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"display_name": ""})
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"display_name": "  "})


def test_teacher_update_rejects_blank_bio() -> None:
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"bio": ""})
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"bio": "   "})


def test_teacher_update_forbids_status_fields() -> None:
    names = set(TeacherUpdate.model_fields)
    assert FORBIDDEN_TEACHER_WRITE_FIELDS & names == set()
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"is_active": False})
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"availability_status": "available"})
    with pytest.raises(ValidationError):
        TeacherUpdate.model_validate({"verification_status": "verified"})


def test_availability_update_literals() -> None:
    for value in ("unknown", "available", "unavailable"):
        parsed = AvailabilityUpdate.model_validate({"availability_status": value})
        assert parsed.availability_status == value
    with pytest.raises(ValidationError):
        AvailabilityUpdate.model_validate({"availability_status": "paused"})
    with pytest.raises(ValidationError):
        AvailabilityUpdate.model_validate({})
    with pytest.raises(ValidationError):
        AvailabilityUpdate.model_validate(
            {"availability_status": "available", "is_active": True}
        )


def test_verification_update_literals() -> None:
    for value in ("unverified", "verified", "rejected"):
        parsed = VerificationUpdate.model_validate({"verification_status": value})
        assert parsed.verification_status == value
    with pytest.raises(ValidationError):
        VerificationUpdate.model_validate({"verification_status": "pending"})
    with pytest.raises(ValidationError):
        VerificationUpdate.model_validate({})
    with pytest.raises(ValidationError):
        VerificationUpdate.model_validate(
            {"verification_status": "verified", "approved_by": "admin"}
        )


def test_admission_create_catalog_omitted_or_null() -> None:
    omitted = AdmissionRecordCreate.model_validate(_admission_create())
    assert omitted.admission_catalog_id is None
    assert "admission_catalog_id" not in omitted.model_fields_set
    explicit_null = AdmissionRecordCreate.model_validate(
        _admission_create(admission_catalog_id=None)
    )
    assert explicit_null.admission_catalog_id is None
    assert "admission_catalog_id" in explicit_null.model_fields_set


def test_admission_create_decimal_and_null_scores() -> None:
    created = AdmissionRecordCreate.model_validate(
        _admission_create(initial_total="321.50", retest_total=85.5, final_total=None)
    )
    assert created.initial_total == Decimal("321.50")
    assert created.retest_total == Decimal("85.5")
    assert created.final_total is None


def test_admission_create_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(initial_total="-0.01"))
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(study_mode="weekend"))
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(admission_year=1999))
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(school_id=0))
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(college_id=-1))


def test_admission_create_forbids_teacher_status_and_timestamps() -> None:
    names = set(AdmissionRecordCreate.model_fields)
    assert FORBIDDEN_ADMISSION_WRITE_FIELDS & names == set()
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(teacher_profile_id=9))
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(is_active=True))
    with pytest.raises(ValidationError):
        AdmissionRecordCreate.model_validate(_admission_create(created_at="2026-01-01"))


def test_admission_update_partial_and_explicit_null() -> None:
    partial = AdmissionRecordUpdate.model_validate({"major_id": 8})
    assert partial.model_dump(exclude_unset=True) == {"major_id": 8}
    assert "school_id" not in partial.model_fields_set
    totals = AdmissionRecordUpdate.model_validate({"initial_total": None})
    assert totals.model_dump(exclude_unset=True) == {"initial_total": None}
    catalog = AdmissionRecordUpdate.model_validate({"admission_catalog_id": None})
    assert catalog.model_dump(exclude_unset=True) == {"admission_catalog_id": None}


def test_admission_update_rejects_null_five_tuple() -> None:
    for field in (
        "school_id",
        "college_id",
        "major_id",
        "admission_year",
        "study_mode",
    ):
        with pytest.raises(ValidationError):
            AdmissionRecordUpdate.model_validate({field: None})


def test_admission_update_rejects_negative_total_and_forbidden_fields() -> None:
    with pytest.raises(ValidationError):
        AdmissionRecordUpdate.model_validate({"retest_total": Decimal(-1)})
    names = set(AdmissionRecordUpdate.model_fields)
    assert FORBIDDEN_ADMISSION_WRITE_FIELDS & names == set()
    with pytest.raises(ValidationError):
        AdmissionRecordUpdate.model_validate({"teacher_profile_id": 1})
    with pytest.raises(ValidationError):
        AdmissionRecordUpdate.model_validate({"is_active": False})


def test_teach_subjects_put_rules() -> None:
    emptied = TeachSubjectsPut.model_validate({"exam_subject_ids": []})
    assert emptied.exam_subject_ids == []
    filled = TeachSubjectsPut.model_validate({"exam_subject_ids": [10, 11, 12]})
    assert filled.exam_subject_ids == [10, 11, 12]
    with pytest.raises(ValidationError):
        TeachSubjectsPut.model_validate({"exam_subject_ids": None})
    with pytest.raises(ValidationError):
        TeachSubjectsPut.model_validate({})
    with pytest.raises(ValidationError):
        TeachSubjectsPut.model_validate({"exam_subject_ids": [10, 10]})
    with pytest.raises(ValidationError):
        TeachSubjectsPut.model_validate({"exam_subject_ids": [0]})
    with pytest.raises(ValidationError):
        TeachSubjectsPut.model_validate({"exam_subject_ids": [-3]})
    with pytest.raises(ValidationError):
        TeachSubjectsPut.model_validate(
            {"exam_subject_ids": [10], "replace_mode": "merge"}
        )


def test_read_schemas_accept_inactive_nested_refs() -> None:
    admission = AdmissionRecordAdminRead.model_validate(_admission_read())
    assert admission.is_active is False
    assert admission.school.is_active is False
    assert admission.college.is_active is False
    assert admission.major.is_active is False
    summary = TeacherAdminSummary.model_validate(
        {
            "id": 9,
            "display_name": "ZZ_S202_T1",
            "bio": None,
            "is_active": False,
            "availability_status": "available",
            "verification_status": "unverified",
        }
    )
    assert summary.is_active is False
    detail = TeacherAdminDetail.model_validate(
        {
            "id": 9,
            "display_name": "ZZ_S202_T1",
            "bio": None,
            "is_active": False,
            "availability_status": "unknown",
            "verification_status": "rejected",
            "admission_records": [_admission_read()],
            "teach_subjects": [INACTIVE_SUBJECT],
        }
    )
    assert detail.admission_records[0].is_active is False
    assert detail.teach_subjects[0].is_active is False


def test_read_schemas_omit_timestamps() -> None:
    for model in (
        TeacherAdminSummary,
        TeacherAdminDetail,
        AdmissionRecordAdminRead,
    ):
        names = set(model.model_fields)
        assert "created_at" not in names
        assert "updated_at" not in names


def test_admission_read_json_scores_are_numbers() -> None:
    admission = AdmissionRecordAdminRead.model_validate(_admission_read())
    payload = json.loads(admission.model_dump_json())
    assert payload["initial_total"] == 321.5
    assert payload["retest_total"] == 85.5
    assert payload["final_total"] == 410.25
    assert isinstance(payload["initial_total"], int | float)
    assert not isinstance(payload["initial_total"], str)
    null_scores = AdmissionRecordAdminRead.model_validate(
        _admission_read(initial_total=None, retest_total=None, final_total=None)
    )
    null_payload = json.loads(null_scores.model_dump_json())
    assert null_payload["initial_total"] is None
    python_dump = admission.model_dump()
    assert python_dump["initial_total"] == Decimal("321.50")
