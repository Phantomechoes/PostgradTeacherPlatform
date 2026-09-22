import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository
from app.repositories.master_data import AdmissionCatalogRepository
from app.schemas.admin_catalog import CatalogAggregatePut, CatalogShellCreate
from app.services.admin_catalog import AdminCatalogService
from app.services.admin_master_data import (
    ConflictError,
    InactiveReferenceError,
    InvalidReferenceError,
    NotFoundError,
    ScopeMismatchError,
)
from tests.conftest import (
    CATALOG_2026_FT_ID,
    CATALOG_2027_ID,
    CATALOG_INACTIVE_COLLEGE_ID,
    CATALOG_INACTIVE_ID,
    CATALOG_SCHOOL_C_ID,
    COLLEGE_A_ID,
    COLLEGE_C_ID,
    COLLEGE_INACTIVE_ID,
    MAJOR_A_ID,
    MAJOR_C_ID,
    SCHOOL_A_ID,
    SCHOOL_C_ID,
    SUBJECT_ALT_ID,
    SUBJECT_INACTIVE_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

SHELL_YEAR = 2035


def _service(session: Session) -> AdminCatalogService:
    return AdminCatalogService(
        AdminCatalogRepository(session),
        AdminSchoolRepository(session),
    )


def _put_body(**overrides: object) -> CatalogAggregatePut:
    payload = {
        "school_id": SCHOOL_A_ID,
        "college_id": COLLEGE_A_ID,
        "major_id": MAJOR_A_ID,
        "admission_year": 2026,
        "study_mode": "full_time",
        "directions": [],
        "exam_units": [],
    }
    payload.update(overrides)
    return CatalogAggregatePut.model_validate(payload)


def test_admin_get_includes_inactive_subject_on_active_legacy_catalog(
    seeded_session: Session,
) -> None:
    detail = _service(seeded_session).get_catalog(CATALOG_2027_ID)
    assert detail.is_active is True
    units = {unit.exam_unit: unit.options for unit in detail.exam_units}
    assert 3 in units
    assert units[3][0].subject.id == SUBJECT_INACTIVE_ID
    assert units[3][0].subject.is_active is False


def test_public_repository_still_hides_inactive_subject(
    seeded_session: Session,
) -> None:
    options = AdmissionCatalogRepository(seeded_session).list_exam_options(
        CATALOG_2027_ID
    )
    subject_ids = {row.subject.id for row in options}
    assert SUBJECT_INACTIVE_ID not in subject_ids
    assert SUBJECT_NATIONAL_ID in subject_ids


def test_create_shell_is_inactive(seeded_session: Session) -> None:
    created = _service(seeded_session).create_shell(
        CatalogShellCreate(
            school_id=SCHOOL_A_ID,
            college_id=COLLEGE_A_ID,
            major_id=MAJOR_A_ID,
            admission_year=SHELL_YEAR,
            study_mode="full_time",
        )
    )
    assert created.is_active is False
    assert created.directions == []
    assert created.exam_units == []
    assert _service(seeded_session).get_catalog(created.id).is_active is False


def test_create_shell_reference_errors(seeded_session: Session) -> None:
    service = _service(seeded_session)
    with pytest.raises(InvalidReferenceError):
        service.create_shell(
            CatalogShellCreate(
                school_id=9_999_999,
                college_id=COLLEGE_A_ID,
                major_id=MAJOR_A_ID,
                admission_year=SHELL_YEAR,
                study_mode="full_time",
            )
        )
    with pytest.raises(InactiveReferenceError) as inactive:
        service.create_shell(
            CatalogShellCreate(
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_INACTIVE_ID,
                major_id=MAJOR_A_ID,
                admission_year=SHELL_YEAR,
                study_mode="part_time",
            )
        )
    assert inactive.value.code == "inactive_reference"
    with pytest.raises(ScopeMismatchError) as scope:
        service.create_shell(
            CatalogShellCreate(
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_C_ID,
                major_id=MAJOR_A_ID,
                admission_year=SHELL_YEAR,
                study_mode="part_time",
            )
        )
    assert scope.value.code == "reference_scope_mismatch"


def test_duplicate_offering_is_conflict(seeded_session: Session) -> None:
    service = _service(seeded_session)
    with pytest.raises(ConflictError) as exc:
        service.create_shell(
            CatalogShellCreate(
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_A_ID,
                major_id=MAJOR_A_ID,
                admission_year=2027,
                study_mode="full_time",
            )
        )
    assert exc.value.code == "duplicate_catalog_offering"


def test_active_put_rejects_inactive_subject(seeded_session: Session) -> None:
    service = _service(seeded_session)
    with pytest.raises(InactiveReferenceError):
        service.replace_aggregate(
            CATALOG_2027_ID,
            _put_body(
                admission_year=2027,
                exam_units=[
                    {
                        "exam_unit": 3,
                        "options": [
                            {
                                "option_order": 1,
                                "exam_subject_id": SUBJECT_INACTIVE_ID,
                            }
                        ],
                    }
                ],
            ),
        )
    repo = AdminCatalogRepository(seeded_session)
    assert [item.direction_code for item in repo.list_directions(CATALOG_2027_ID)] == [
        "01",
        "02",
    ]
    kept = {row.subject.id for row in repo.list_exam_options(CATALOG_2027_ID)}
    assert SUBJECT_INACTIVE_ID in kept


def test_active_put_can_repair_legacy_catalog(seeded_session: Session) -> None:
    detail = _service(seeded_session).replace_aggregate(
        CATALOG_2027_ID,
        _put_body(
            admission_year=2027,
            directions=[
                {"direction_code": "01", "direction_name": "kept"},
            ],
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {
                            "option_order": 1,
                            "exam_subject_id": SUBJECT_NATIONAL_ID,
                        }
                    ],
                },
                {
                    "exam_unit": 2,
                    "options": [
                        {
                            "option_order": 1,
                            "exam_subject_id": SUBJECT_SCHOOL_ID,
                        },
                        {
                            "option_order": 3,
                            "exam_subject_id": SUBJECT_ALT_ID,
                        },
                    ],
                },
            ],
        ),
    )
    units = {unit.exam_unit for unit in detail.exam_units}
    assert 3 not in units
    assert [item.direction_code for item in detail.directions] == ["01"]
    assert detail.exam_units[1].options[1].option_order == 3


def test_inactive_put_allows_inactive_subject(seeded_session: Session) -> None:
    detail = _service(seeded_session).replace_aggregate(
        CATALOG_INACTIVE_ID,
        _put_body(
            admission_year=2028,
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {
                            "option_order": 1,
                            "exam_subject_id": SUBJECT_INACTIVE_ID,
                        }
                    ],
                }
            ],
        ),
    )
    assert detail.is_active is False
    assert detail.exam_units[0].options[0].subject.is_active is False


def test_other_school_subject_is_scope_mismatch(seeded_session: Session) -> None:
    service = _service(seeded_session)
    with pytest.raises(ScopeMismatchError):
        service.replace_aggregate(
            CATALOG_INACTIVE_ID,
            _put_body(
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_C_ID,
                major_id=MAJOR_A_ID,
                admission_year=2028,
            ),
        )
    with pytest.raises(ScopeMismatchError):
        service.replace_aggregate(
            CATALOG_SCHOOL_C_ID,
            _put_body(
                school_id=SCHOOL_C_ID,
                college_id=COLLEGE_C_ID,
                major_id=MAJOR_C_ID,
                admission_year=2027,
                exam_units=[
                    {
                        "exam_unit": 1,
                        "options": [
                            {
                                "option_order": 1,
                                "exam_subject_id": SUBJECT_SCHOOL_ID,
                            }
                        ],
                    }
                ],
            ),
        )


def test_activate_requires_active_refs(seeded_session: Session) -> None:
    service = _service(seeded_session)
    with pytest.raises(InactiveReferenceError):
        service.set_status(CATALOG_INACTIVE_COLLEGE_ID, True)
    restored = service.set_status(CATALOG_INACTIVE_ID, True)
    assert restored.is_active is True
    deactivated = service.set_status(CATALOG_INACTIVE_ID, False)
    assert deactivated.is_active is False
    assert deactivated.directions == restored.directions


def test_list_includes_inactive_and_missing_school_is_empty(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    page = service.list_catalogs(
        school_id=SCHOOL_A_ID,
        status="inactive",
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode=None,
        page=1,
        page_size=20,
    )
    ids = {item.id for item in page.items}
    assert CATALOG_INACTIVE_ID in ids
    assert CATALOG_2027_ID not in ids
    empty = service.list_catalogs(
        school_id=9_999_999,
        status="all",
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode=None,
        page=1,
        page_size=20,
    )
    assert empty.total == 0


def test_not_found_catalog(seeded_session: Session) -> None:
    with pytest.raises(NotFoundError):
        _service(seeded_session).get_catalog(9_999_999)


def test_failed_put_does_not_keep_partial_changes(seeded_session: Session) -> None:
    service = _service(seeded_session)
    nested = seeded_session.begin_nested()
    with pytest.raises(ConflictError) as exc:
        service.replace_aggregate(
            CATALOG_2026_FT_ID,
            _put_body(admission_year=2027, study_mode="full_time"),
        )
    assert exc.value.code == "duplicate_catalog_offering"
    nested.rollback()
    detail = service.get_catalog(CATALOG_2026_FT_ID)
    assert detail.admission_year == 2026
    assert detail.study_mode == "full_time"


def _active_subject_units() -> list[dict[str, object]]:
    return [
        {
            "exam_unit": 1,
            "options": [
                {"option_order": 1, "exam_subject_id": SUBJECT_NATIONAL_ID},
            ],
        },
        {
            "exam_unit": 2,
            "options": [
                {"option_order": 1, "exam_subject_id": SUBJECT_SCHOOL_ID},
                {"option_order": 3, "exam_subject_id": SUBJECT_ALT_ID},
            ],
        },
    ]


def test_put_empty_directions_removes_existing_directions(
    seeded_session: Session,
) -> None:
    repo = AdminCatalogRepository(seeded_session)
    assert [item.direction_code for item in repo.list_directions(CATALOG_2027_ID)] == [
        "01",
        "02",
    ]
    _service(seeded_session).replace_aggregate(
        CATALOG_2027_ID,
        _put_body(
            admission_year=2027,
            directions=[],
            exam_units=_active_subject_units(),
        ),
    )
    assert repo.list_directions(CATALOG_2027_ID) == []


def test_deactivate_keeps_children(seeded_session: Session) -> None:
    repo = AdminCatalogRepository(seeded_session)
    detail = _service(seeded_session).set_status(CATALOG_2027_ID, False)
    assert detail.is_active is False
    assert [item.direction_code for item in repo.list_directions(CATALOG_2027_ID)] == [
        "01",
        "02",
    ]
    kept = {row.subject.id for row in repo.list_exam_options(CATALOG_2027_ID)}
    assert kept == {
        SUBJECT_NATIONAL_ID,
        SUBJECT_SCHOOL_ID,
        SUBJECT_ALT_ID,
        SUBJECT_INACTIVE_ID,
    }


def test_legacy_active_catalog_reactivate_revalidates(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    with pytest.raises(InactiveReferenceError) as exc:
        service.set_status(CATALOG_2027_ID, True)
    assert exc.value.code == "inactive_reference"
    detail = service.get_catalog(CATALOG_2027_ID)
    assert detail.is_active is True
    assert [item.direction_code for item in detail.directions] == ["01", "02"]


def test_legacy_active_catalog_repaired_by_one_put(seeded_session: Session) -> None:
    detail = _service(seeded_session).replace_aggregate(
        CATALOG_2027_ID,
        _put_body(
            admission_year=2027,
            directions=[{"direction_code": "01", "direction_name": "kept"}],
            exam_units=_active_subject_units(),
        ),
    )
    assert detail.is_active is True
    subjects = [
        option.subject
        for unit in detail.exam_units
        for option in unit.options
    ]
    assert SUBJECT_INACTIVE_ID not in {subject.id for subject in subjects}
    assert subjects
    assert all(subject.is_active for subject in subjects)


def test_inactive_put_missing_subject_is_invalid_reference(
    seeded_session: Session,
) -> None:
    with pytest.raises(InvalidReferenceError) as exc:
        _service(seeded_session).replace_aggregate(
            CATALOG_INACTIVE_ID,
            _put_body(
                admission_year=2028,
                exam_units=[
                    {
                        "exam_unit": 1,
                        "options": [
                            {"option_order": 1, "exam_subject_id": 9_999_999},
                        ],
                    }
                ],
            ),
        )
    assert exc.value.code == "invalid_reference"


class _RecordingMasters:
    def __init__(self) -> None:
        self.bulk_calls: list[list[int]] = []

    def get_exam_subjects_by_ids(self, subject_ids: list[int]) -> list[object]:
        self.bulk_calls.append(list(subject_ids))
        return [
            _LoadedSubject(subject_id)
            for subject_id in subject_ids
        ]


class _LoadedSubject:
    def __init__(self, subject_id: int) -> None:
        self.id = subject_id
        self.school_id = None
        self.is_active = True


def test_many_options_load_subjects_in_one_bulk_call() -> None:
    masters = _RecordingMasters()
    service = AdminCatalogService(object(), masters)  # type: ignore[arg-type]
    service._validate_subjects(
        catalog_school_id=SCHOOL_A_ID,
        exam_units=[
            _Unit([_Option(11), _Option(12)]),
            _Unit([_Option(11), _Option(13)]),
        ],
        require_active=True,
    )
    assert masters.bulk_calls == [[11, 12, 13]]


class _Option:
    def __init__(self, exam_subject_id: int) -> None:
        self.exam_subject_id = exam_subject_id


class _Unit:
    def __init__(self, options: list[_Option]) -> None:
        self.options = options


def test_unknown_integrity_error_is_reraised() -> None:
    class _Catalogs:
        def flush(self) -> None:
            raise IntegrityError("INSERT", {}, Exception("mystery"))

    service = AdminCatalogService(_Catalogs(), object())  # type: ignore[arg-type]
    with pytest.raises(IntegrityError):
        service._flush()
