import pytest
from pydantic import ValidationError

from app.schemas.admin_master_data import (
    CollegeCreate,
    CollegeUpdate,
    ExamSubjectCreate,
    ExamSubjectUpdate,
    MajorCreate,
    MajorUpdate,
    SchoolAdminRead,
    SchoolCreate,
    SchoolUpdate,
    StatusUpdate,
)

FORBIDDEN_WRITE_FIELDS = frozenset(
    {"id", "school_id", "is_active", "created_at", "updated_at"}
)
UPDATE_MODELS = (
    SchoolUpdate,
    CollegeUpdate,
    MajorUpdate,
    ExamSubjectUpdate,
)
CREATE_MODELS = (
    SchoolCreate,
    CollegeCreate,
    MajorCreate,
    ExamSubjectCreate,
)


def test_update_and_create_schemas_exclude_scope_and_status_fields() -> None:
    for model in (*CREATE_MODELS, *UPDATE_MODELS):
        names = set(model.model_fields)
        assert FORBIDDEN_WRITE_FIELDS & names == set(), model.__name__
    assert set(StatusUpdate.model_fields) == {"is_active"}


def test_status_update_requires_boolean() -> None:
    assert StatusUpdate(is_active=True).is_active is True
    with pytest.raises(ValidationError):
        StatusUpdate.model_validate({})
    with pytest.raises(ValidationError):
        StatusUpdate.model_validate({"is_active": None})


def test_major_degree_type_must_be_enum() -> None:
    MajorCreate(major_code="140500", name="智能科学与技术", degree_type="academic")
    with pytest.raises(ValidationError):
        MajorCreate(
            major_code="140500",
            name="智能科学与技术",
            degree_type="doctoral",  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        MajorUpdate(degree_type="other")  # type: ignore[arg-type]


def test_school_update_partial_dump_excludes_unset() -> None:
    dumped = SchoolUpdate(name="新名称").model_dump(exclude_unset=True)
    assert dumped == {"name": "新名称"}
    assert "school_code" not in dumped


def test_admin_read_has_is_active_not_timestamps() -> None:
    fields = set(SchoolAdminRead.model_fields)
    assert "is_active" in fields
    assert "created_at" not in fields
    assert "updated_at" not in fields


def test_explicit_null_rejected_except_college_code() -> None:
    with pytest.raises(ValidationError):
        SchoolUpdate.model_validate({"name": None})
    with pytest.raises(ValidationError):
        CollegeUpdate.model_validate({"name": None})
    cleared = CollegeUpdate.model_validate({"college_code": None})
    assert cleared.model_dump(exclude_unset=True) == {"college_code": None}
    with pytest.raises(ValidationError):
        MajorUpdate.model_validate({"major_code": None})
    with pytest.raises(ValidationError):
        MajorUpdate.model_validate({"degree_type": None})
    with pytest.raises(ValidationError):
        ExamSubjectUpdate.model_validate({"subject_code": None})


def test_write_schemas_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SchoolUpdate.model_validate({"name": "x", "school_id": 1})
    with pytest.raises(ValidationError):
        MajorUpdate.model_validate({"school_id": 123})
    with pytest.raises(ValidationError):
        ExamSubjectUpdate.model_validate({"school_id": None})
    with pytest.raises(ValidationError):
        StatusUpdate.model_validate({"is_active": False, "name": "x"})
