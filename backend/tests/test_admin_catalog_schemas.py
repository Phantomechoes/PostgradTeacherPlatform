import pytest
from pydantic import ValidationError

from app.schemas.admin_catalog import (
    CatalogAggregatePut,
    CatalogShellCreate,
    DirectionWrite,
    ExamUnitWrite,
)


def _put(**overrides: object) -> CatalogAggregatePut:
    payload = {
        "school_id": 1,
        "college_id": 2,
        "major_id": 3,
        "admission_year": 2026,
        "study_mode": "full_time",
        "directions": [],
        "exam_units": [],
    }
    payload.update(overrides)
    return CatalogAggregatePut.model_validate(payload)


def _shell(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "school_id": 1,
        "college_id": 2,
        "major_id": 3,
        "admission_year": 2026,
        "study_mode": "full_time",
    }
    payload.update(overrides)
    return payload


def test_shell_forbids_is_active_and_children() -> None:
    with pytest.raises(ValidationError):
        CatalogShellCreate.model_validate(_shell(is_active=True))
    with pytest.raises(ValidationError):
        CatalogShellCreate.model_validate(_shell(directions=[]))
    with pytest.raises(ValidationError):
        CatalogShellCreate.model_validate(_shell(exam_units=[]))


def test_put_requires_collections_and_forbids_child_ids() -> None:
    base = {
        "school_id": 1,
        "college_id": 2,
        "major_id": 3,
        "admission_year": 2026,
        "study_mode": "full_time",
    }
    with pytest.raises(ValidationError):
        CatalogAggregatePut.model_validate(base)
    with pytest.raises(ValidationError):
        CatalogAggregatePut.model_validate({**base, "exam_units": []})
    with pytest.raises(ValidationError):
        CatalogAggregatePut.model_validate({**base, "directions": []})
    with pytest.raises(ValidationError):
        DirectionWrite.model_validate(
            {"id": 9, "direction_code": "01", "direction_name": "x"}
        )


def test_put_rejects_duplicate_direction_and_unit() -> None:
    with pytest.raises(ValidationError):
        _put(
            directions=[
                {"direction_code": "01", "direction_name": "a"},
                {"direction_code": "01", "direction_name": "b"},
            ]
        )
    with pytest.raises(ValidationError):
        _put(
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [{"option_order": 1, "exam_subject_id": 1}],
                },
                {
                    "exam_unit": 1,
                    "options": [{"option_order": 1, "exam_subject_id": 2}],
                },
            ]
        )


def test_exam_unit_options_cannot_be_empty_or_duplicate() -> None:
    with pytest.raises(ValidationError):
        ExamUnitWrite.model_validate({"exam_unit": 1, "options": []})
    with pytest.raises(ValidationError):
        ExamUnitWrite.model_validate(
            {
                "exam_unit": 2,
                "options": [
                    {"option_order": 1, "exam_subject_id": 1},
                    {"option_order": 1, "exam_subject_id": 2},
                ],
            }
        )
    with pytest.raises(ValidationError):
        ExamUnitWrite.model_validate(
            {
                "exam_unit": 2,
                "options": [
                    {"option_order": 1, "exam_subject_id": 8},
                    {"option_order": 3, "exam_subject_id": 8},
                ],
            }
        )


def test_non_contiguous_option_order_is_allowed() -> None:
    unit = ExamUnitWrite.model_validate(
        {
            "exam_unit": 2,
            "options": [
                {"option_order": 1, "exam_subject_id": 1},
                {"option_order": 3, "exam_subject_id": 2},
            ],
        }
    )
    assert [item.option_order for item in unit.options] == [1, 3]


def test_empty_collections_are_allowed_on_put() -> None:
    payload = _put(directions=[], exam_units=[])
    assert payload.directions == []
    assert payload.exam_units == []
