import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.admin_master_data import AdminSchoolRepository
from app.schemas.admin_master_data import (
    CollegeCreate,
    CollegeUpdate,
    ExamSubjectCreate,
    ExamSubjectUpdate,
    MajorCreate,
    SchoolCreate,
    SchoolUpdate,
)
from app.services.admin_master_data import (
    AdminMasterDataService,
    CheckViolationError,
    ConflictError,
    InvalidReferenceError,
    NotFoundError,
    ParentInactiveError,
    _map_integrity_error,
)
from tests.conftest import (
    COLLEGE_INACTIVE_ID,
    PREFIX,
    SCHOOL_A_ID,
    SCHOOL_B_INACTIVE_ID,
    SUBJECT_INACTIVE_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

WRITE_PREFIX = "ZZ_TEST_S103A"


def _service(session: Session) -> AdminMasterDataService:
    return AdminMasterDataService(AdminSchoolRepository(session))


def test_create_school(seeded_session: Session) -> None:
    created = _service(seeded_session).create_school(
        SchoolCreate(school_code=f"{WRITE_PREFIX}_S", name=f"{WRITE_PREFIX}_School")
    )
    assert created.is_active is True
    assert created.school_code == f"{WRITE_PREFIX}_S"


def test_create_college_requires_active_parent(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_college(
        SCHOOL_A_ID,
        CollegeCreate(college_code="NEWC", name=f"{WRITE_PREFIX}_COL"),
    )
    assert created.school_id == SCHOOL_A_ID
    assert created.is_active is True

    with pytest.raises(ParentInactiveError) as inactive:
        service.create_college(
            SCHOOL_B_INACTIVE_ID,
            CollegeCreate(name=f"{WRITE_PREFIX}_NO"),
        )
    assert inactive.value.code == "parent_inactive"

    with pytest.raises(NotFoundError) as missing:
        service.create_college(9_999_999, CollegeCreate(name=f"{WRITE_PREFIX}_NO"))
    assert missing.value.code == "not_found"


def test_inactive_child_can_be_patched_and_reactivated(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    updated = service.update_college(
        COLLEGE_INACTIVE_ID,
        CollegeUpdate(name=f"{WRITE_PREFIX}_RENAMED"),
    )
    assert updated.id == COLLEGE_INACTIVE_ID
    assert updated.is_active is False
    assert updated.name == f"{WRITE_PREFIX}_RENAMED"

    restored = service.set_college_status(COLLEGE_INACTIVE_ID, True)
    assert restored.is_active is True


def test_inactive_school_is_readable_not_missing(seeded_session: Session) -> None:
    school = _service(seeded_session).get_school(SCHOOL_B_INACTIVE_ID)
    assert school.is_active is False


def test_duplicate_school_code_is_conflict(seeded_session: Session) -> None:
    service = _service(seeded_session)
    with pytest.raises(ConflictError) as exc:
        service.create_school(
            SchoolCreate(school_code=f"{PREFIX}_A", name=f"{WRITE_PREFIX}_Dup")
        )
    assert exc.value.code == "duplicate_school_code"


def test_null_college_codes_may_repeat_in_same_school(seeded_session: Session) -> None:
    service = _service(seeded_session)
    first = service.create_college(SCHOOL_A_ID, CollegeCreate(name=f"{WRITE_PREFIX}_N1"))
    second = service.create_college(
        SCHOOL_A_ID, CollegeCreate(name=f"{WRITE_PREFIX}_N2")
    )
    assert first.college_code is None
    assert second.college_code is None
    assert first.id != second.id


def test_national_exam_subject_has_null_school_id(seeded_session: Session) -> None:
    created = _service(seeded_session).create_national_exam_subject(
        ExamSubjectCreate(subject_code=f"{WRITE_PREFIX}_201", name="英语一")
    )
    assert created.school_id is None
    assert created.is_active is True


def test_school_exam_subject_keeps_path_school_id(seeded_session: Session) -> None:
    created = _service(seeded_session).create_school_exam_subject(
        SCHOOL_A_ID,
        ExamSubjectCreate(subject_code=f"{WRITE_PREFIX}_896", name="自命题"),
    )
    assert created.school_id == SCHOOL_A_ID


def test_exam_subject_update_cannot_change_scope(seeded_session: Session) -> None:
    service = _service(seeded_session)
    dumped = ExamSubjectUpdate(name="新名称").model_dump(exclude_unset=True)
    assert "school_id" not in dumped

    national = service.update_exam_subject(
        SUBJECT_NATIONAL_ID,
        ExamSubjectUpdate(name=f"{WRITE_PREFIX}_NAT"),
    )
    assert national.school_id is None

    school_subject = service.update_exam_subject(
        SUBJECT_SCHOOL_ID,
        ExamSubjectUpdate(name=f"{WRITE_PREFIX}_SCH"),
    )
    assert school_subject.school_id == SCHOOL_A_ID

    restored = service.set_exam_subject_status(SUBJECT_INACTIVE_ID, True)
    assert restored.is_active is True
    assert restored.school_id == SCHOOL_A_ID


def test_create_major_and_duplicate_code(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_major(
        SCHOOL_A_ID,
        MajorCreate(
            major_code=f"{WRITE_PREFIX}_140510",
            name=f"{WRITE_PREFIX}_M",
            degree_type="professional",
        ),
    )
    assert created.school_id == SCHOOL_A_ID
    with pytest.raises(ConflictError) as exc:
        service.create_major(
            SCHOOL_A_ID,
            MajorCreate(
                major_code=f"{PREFIX}_140500",
                name="dup",
                degree_type="academic",
            ),
        )
    assert exc.value.code == "duplicate_major_code"


def _integrity(sqlstate: str, constraint_name: str) -> IntegrityError:
    orig = type(
        "Orig",
        (),
        {
            "sqlstate": sqlstate,
            "diag": type("Diag", (), {"constraint_name": constraint_name})(),
        },
    )()
    return IntegrityError("INSERT", {}, orig)


def test_known_constraints_map_to_domain_errors() -> None:
    duplicate = _map_integrity_error(
        _integrity("23505", "uq_schools_school_code")
    )
    assert isinstance(duplicate, ConflictError)
    assert duplicate.code == "duplicate_school_code"

    fk = _map_integrity_error(_integrity("23503", "fk_colleges_school_id"))
    assert isinstance(fk, InvalidReferenceError)

    check = _map_integrity_error(_integrity("23514", "ck_majors_degree_type"))
    assert isinstance(check, CheckViolationError)


def test_unknown_integrity_errors_are_not_wrapped() -> None:
    unknown_fk = _integrity("23503", "unknown_fk")
    assert _map_integrity_error(unknown_fk) is unknown_fk

    unknown_check = _integrity("23514", "unknown_check")
    assert _map_integrity_error(unknown_check) is unknown_check


def test_patch_school_partial(seeded_session: Session) -> None:
    updated = _service(seeded_session).update_school(
        SCHOOL_A_ID,
        SchoolUpdate(name=f"{WRITE_PREFIX}_Alpha"),
    )
    assert updated.id == SCHOOL_A_ID
    assert updated.name == f"{WRITE_PREFIX}_Alpha"
    assert updated.school_code == f"{PREFIX}_A"
