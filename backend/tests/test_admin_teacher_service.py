from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AdmissionCatalog, College, ExamSubject, Major, School
from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository
from app.repositories.admin_teacher import AdminTeacherRepository
from app.schemas.admin_teacher import (
    AdmissionRecordAdminRead,
    AdmissionRecordCreate,
    AdmissionRecordUpdate,
    TeacherAdminDetail,
    TeacherCreate,
    TeacherUpdate,
    TeachSubjectsPut,
)
from app.services.admin_master_data import (
    CheckViolationError,
    ConflictError,
    EmptyPatchError,
    InactiveReferenceError,
    InvalidReferenceError,
    NotFoundError,
    ParentInactiveError,
    ScopeMismatchError,
)
from app.services.admin_teacher import (
    AdminTeacherService,
    CatalogIdentityMismatchError,
)
from tests.conftest import (
    CATALOG_2026_FT_ID,
    CATALOG_2027_ID,
    CATALOG_INACTIVE_ID,
    COLLEGE_A_ID,
    COLLEGE_B_ID,
    COLLEGE_C_ID,
    COLLEGE_INACTIVE_ID,
    MAJOR_A2_ID,
    MAJOR_A_ID,
    MAJOR_C_ID,
    MAJOR_INACTIVE_ID,
    SCHOOL_A_ID,
    SCHOOL_B_INACTIVE_ID,
    SCHOOL_C_ID,
    SUBJECT_ALT_ID,
    SUBJECT_INACTIVE_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

PREFIX = "ZZS202S"


def _service(session: Session) -> AdminTeacherService:
    return AdminTeacherService(
        AdminTeacherRepository(session),
        AdminSchoolRepository(session),
        AdminCatalogRepository(session),
    )


def _teacher(service: AdminTeacherService, name: str) -> int:
    return service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} {name}")
    ).id


def _admission(**overrides: object) -> AdmissionRecordCreate:
    payload: dict[str, object] = {
        "school_id": SCHOOL_A_ID,
        "college_id": COLLEGE_A_ID,
        "major_id": MAJOR_A_ID,
        "admission_year": 2025,
        "study_mode": "full_time",
    }
    payload.update(overrides)
    return AdmissionRecordCreate.model_validate(payload)


def _active_children(
    session: Session,
    school_id: int,
    code: str,
) -> tuple[int, int]:
    college = College(
        school_id=school_id,
        college_code=code,
        name=f"{PREFIX}_{code}",
        is_active=True,
    )
    major = Major(
        school_id=school_id,
        major_code=code,
        name=f"{PREFIX}_{code}",
        degree_type="academic",
        is_active=True,
    )
    session.add_all([college, major])
    session.flush()
    return college.id, major.id


def _subject_ids(session: Session, teacher_id: int) -> list[int]:
    rows = AdminTeacherRepository(session).list_teach_subjects_for_teacher(
        teacher_id
    )
    return [row.subject.id for row in rows]


def _put(
    service: AdminTeacherService,
    teacher_id: int,
    subject_ids: list[int],
) -> TeacherAdminDetail:
    return service.replace_teach_subjects(
        teacher_id,
        TeachSubjectsPut(exam_subject_ids=subject_ids),
    )


def _seed_subjects(
    service: AdminTeacherService,
    name: str,
    subject_ids: list[int],
    *,
    active: bool = True,
) -> int:
    teacher_id = _teacher(service, name)
    if subject_ids:
        _put(service, teacher_id, subject_ids)
    if not active:
        service.set_teacher_status(teacher_id, False)
    return teacher_id


def _assert_subject_set(
    session: Session,
    teacher_id: int,
    expected: list[int],
    detail: TeacherAdminDetail | None = None,
) -> None:
    stored = _subject_ids(session, teacher_id)
    assert stored == sorted(expected)
    if detail is not None:
        assert [subject.id for subject in detail.teach_subjects] == stored


def test_create_teacher_defaults(seeded_session: Session) -> None:
    created = _service(seeded_session).create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Defaults")
    )
    assert created.display_name == f"{PREFIX} Defaults"
    assert created.bio is None
    assert created.is_active is True
    assert created.availability_status == "unknown"
    assert created.verification_status == "unverified"


def test_update_display_name(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Name", bio="keep bio")
    )
    updated = service.update_teacher(
        created.id,
        TeacherUpdate(display_name=f"{PREFIX} Renamed"),
    )
    assert updated.id == created.id
    assert updated.display_name == f"{PREFIX} Renamed"
    assert updated.bio == "keep bio"
    assert updated.is_active is True
    assert updated.availability_status == "unknown"
    assert updated.verification_status == "unverified"


def test_update_bio(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Bio", bio="old bio")
    )
    updated = service.update_teacher(
        created.id,
        TeacherUpdate(bio="new bio"),
    )
    assert updated.display_name == f"{PREFIX} Bio"
    assert updated.bio == "new bio"


def test_update_bio_null_clears_bio(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Clear Bio", bio="to clear")
    )
    updated = service.update_teacher(created.id, TeacherUpdate(bio=None))
    assert updated.display_name == f"{PREFIX} Clear Bio"
    assert updated.bio is None


def test_empty_patch_is_rejected(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Empty", bio="stays")
    )
    with pytest.raises(EmptyPatchError) as exc:
        service.update_teacher(created.id, TeacherUpdate())
    assert exc.value.code == "empty_patch"
    detail = service.get_teacher(created.id)
    assert detail.display_name == f"{PREFIX} Empty"
    assert detail.bio == "stays"


def test_set_teacher_status(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(TeacherCreate(display_name=f"{PREFIX} Status"))
    inactive = service.set_teacher_status(created.id, False)
    assert inactive.is_active is False
    assert inactive.availability_status == "unknown"
    assert inactive.verification_status == "unverified"
    active = service.set_teacher_status(created.id, True)
    assert active.is_active is True
    assert active.availability_status == "unknown"
    assert active.verification_status == "unverified"


def test_set_availability(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Availability")
    )
    updated = service.set_availability(created.id, "available")
    assert updated.availability_status == "available"
    assert updated.is_active is True
    assert updated.verification_status == "unverified"
    updated = service.set_availability(created.id, "unavailable")
    assert updated.availability_status == "unavailable"
    assert updated.is_active is True
    assert updated.verification_status == "unverified"


def test_set_verification(seeded_session: Session) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Verification")
    )
    updated = service.set_verification(created.id, "verified")
    assert updated.verification_status == "verified"
    assert updated.is_active is True
    assert updated.availability_status == "unknown"
    updated = service.set_verification(created.id, "rejected")
    assert updated.verification_status == "rejected"
    assert updated.is_active is True
    assert updated.availability_status == "unknown"


def test_status_availability_and_verification_are_orthogonal(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Orthogonal", bio="bio")
    )
    status = service.set_teacher_status(created.id, False)
    assert status.is_active is False
    assert status.availability_status == "unknown"
    assert status.verification_status == "unverified"
    assert status.bio == "bio"

    availability = service.set_availability(created.id, "available")
    assert availability.is_active is False
    assert availability.availability_status == "available"
    assert availability.verification_status == "unverified"

    verification = service.set_verification(created.id, "verified")
    assert verification.is_active is False
    assert verification.availability_status == "available"
    assert verification.verification_status == "verified"
    assert verification.display_name == f"{PREFIX} Orthogonal"
    assert verification.bio == "bio"


def test_inactive_teacher_profile_can_be_updated_and_restored(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    created = service.create_teacher(
        TeacherCreate(display_name=f"{PREFIX} Inactive", bio="old")
    )
    service.set_teacher_status(created.id, False)

    renamed = service.update_teacher(
        created.id,
        TeacherUpdate(display_name=f"{PREFIX} Inactive Renamed"),
    )
    assert renamed.is_active is False
    assert renamed.display_name == f"{PREFIX} Inactive Renamed"
    assert renamed.bio == "old"

    cleared = service.update_teacher(created.id, TeacherUpdate(bio=None))
    assert cleared.is_active is False
    assert cleared.bio is None
    assert cleared.display_name == f"{PREFIX} Inactive Renamed"

    availability = service.set_availability(created.id, "unavailable")
    assert availability.is_active is False
    assert availability.availability_status == "unavailable"
    assert availability.verification_status == "unverified"

    verification = service.set_verification(created.id, "rejected")
    assert verification.is_active is False
    assert verification.availability_status == "unavailable"
    assert verification.verification_status == "rejected"

    restored = service.set_teacher_status(created.id, True)
    assert restored.is_active is True
    assert restored.display_name == f"{PREFIX} Inactive Renamed"
    assert restored.bio is None
    assert restored.availability_status == "unavailable"
    assert restored.verification_status == "rejected"


def test_create_admission_without_catalog(seeded_session: Session) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Create")
    created = service.create_admission(
        teacher_id,
        _admission(
            initial_total=Decimal("350.25"),
            retest_total=Decimal("80.00"),
            final_total=Decimal("70.50"),
        ),
    )
    assert isinstance(created, AdmissionRecordAdminRead)
    assert created.teacher_profile_id == teacher_id
    assert created.is_active is True
    assert created.admission_catalog_id is None
    assert created.school.id == SCHOOL_A_ID
    assert created.school.is_active is True
    assert created.college.id == COLLEGE_A_ID
    assert created.college.is_active is True
    assert created.major.id == MAJOR_A_ID
    assert created.major.is_active is True
    assert created.admission_year == 2025
    assert created.study_mode == "full_time"
    assert created.initial_total == Decimal("350.25")
    assert created.retest_total == Decimal("80.00")
    assert created.final_total == Decimal("70.50")


def test_create_admission_allows_matching_catalog_active_or_inactive(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Matching Catalog")
    active = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2027,
            admission_catalog_id=CATALOG_2027_ID,
        ),
    )
    assert active.admission_catalog_id == CATALOG_2027_ID
    assert active.admission_year == 2027
    assert active.study_mode == "full_time"
    assert active.school.id == SCHOOL_A_ID
    assert active.college.id == COLLEGE_A_ID
    assert active.major.id == MAJOR_A_ID

    inactive = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2028,
            admission_catalog_id=CATALOG_INACTIVE_ID,
        ),
    )
    assert inactive.admission_catalog_id == CATALOG_INACTIVE_ID
    assert inactive.admission_year == 2028
    catalog = seeded_session.get(AdmissionCatalog, CATALOG_INACTIVE_ID)
    assert catalog is not None
    assert catalog.is_active is False


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {
                "admission_year": 2027,
                "admission_catalog_id": CATALOG_2026_FT_ID,
            },
            id="year",
        ),
        pytest.param(
            {
                "admission_year": 2026,
                "study_mode": "part_time",
                "admission_catalog_id": CATALOG_2026_FT_ID,
            },
            id="study_mode",
        ),
        pytest.param(
            {
                "college_id": COLLEGE_B_ID,
                "admission_year": 2027,
                "admission_catalog_id": CATALOG_2027_ID,
            },
            id="college",
        ),
        pytest.param(
            {
                "major_id": MAJOR_A2_ID,
                "admission_year": 2027,
                "admission_catalog_id": CATALOG_2027_ID,
            },
            id="major",
        ),
        pytest.param(
            {
                "school_id": SCHOOL_C_ID,
                "college_id": COLLEGE_C_ID,
                "major_id": MAJOR_C_ID,
                "admission_year": 2027,
                "admission_catalog_id": CATALOG_2027_ID,
            },
            id="school",
        ),
    ],
)
def test_create_admission_rejects_catalog_identity_mismatch(
    seeded_session: Session,
    overrides: dict[str, object],
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Catalog Mismatch")
    with pytest.raises(CatalogIdentityMismatchError) as exc:
        service.create_admission(teacher_id, _admission(**overrides))
    assert exc.value.code == "catalog_identity_mismatch"
    assert service.get_teacher(teacher_id).admission_records == []


def test_create_admission_rejects_missing_master_ref(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Missing Ref")
    cases: tuple[tuple[str, dict[str, object]], ...] = (
        ("school", {"school_id": 9_999_991}),
        ("college", {"college_id": 9_999_992}),
        ("major", {"major_id": 9_999_993}),
    )
    for resource, overrides in cases:
        with pytest.raises(InvalidReferenceError) as exc:
            service.create_admission(teacher_id, _admission(**overrides))
        assert exc.value.code == "invalid_reference"
        assert resource in exc.value.message
    assert service.get_teacher(teacher_id).admission_records == []


def test_create_admission_rejects_inactive_master_ref(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Inactive Ref")
    college_id, major_id = _active_children(
        seeded_session,
        SCHOOL_B_INACTIVE_ID,
        "BINACT",
    )
    cases: tuple[tuple[str, dict[str, object]], ...] = (
        ("college", {"college_id": COLLEGE_INACTIVE_ID}),
        ("major", {"major_id": MAJOR_INACTIVE_ID}),
        (
            "school",
            {
                "school_id": SCHOOL_B_INACTIVE_ID,
                "college_id": college_id,
                "major_id": major_id,
            },
        ),
    )
    for resource, overrides in cases:
        with pytest.raises(InactiveReferenceError) as exc:
            service.create_admission(teacher_id, _admission(**overrides))
        assert exc.value.code == "inactive_reference"
        assert exc.value.resource == resource
    assert service.get_teacher(teacher_id).admission_records == []


def test_create_admission_rejects_cross_school_college(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Cross College")
    with pytest.raises(ScopeMismatchError) as exc:
        service.create_admission(
            teacher_id,
            _admission(college_id=COLLEGE_C_ID),
        )
    assert exc.value.code == "reference_scope_mismatch"
    assert "college" in exc.value.message
    assert service.get_teacher(teacher_id).admission_records == []


def test_create_admission_rejects_cross_school_major(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Cross Major")
    with pytest.raises(ScopeMismatchError) as exc:
        service.create_admission(
            teacher_id,
            _admission(major_id=MAJOR_C_ID),
        )
    assert exc.value.code == "reference_scope_mismatch"
    assert "major" in exc.value.message
    assert service.get_teacher(teacher_id).admission_records == []


def test_create_admission_rejects_inactive_teacher(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Inactive Teacher")
    service.set_teacher_status(teacher_id, False)
    with pytest.raises(ParentInactiveError) as exc:
        service.create_admission(teacher_id, _admission())
    assert exc.value.code == "parent_inactive"
    assert exc.value.resource == "teacher_profile"
    assert service.get_teacher(teacher_id).admission_records == []


def test_create_duplicate_admission(seeded_session: Session) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Duplicate Create")
    payload = _admission(admission_year=2021)
    service.create_admission(teacher_id, payload)
    nested = seeded_session.begin_nested()
    with pytest.raises(ConflictError) as exc:
        service.create_admission(teacher_id, payload)
    assert exc.value.code == "duplicate_admission"
    nested.rollback()
    seeded_session.expire_all()
    records = service.get_teacher(teacher_id).admission_records
    assert len(records) == 1
    assert records[0].admission_year == 2021
    assert records[0].is_active is True


def test_patch_admission_partial_score(seeded_session: Session) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Partial Score")
    created = service.create_admission(
        teacher_id,
        _admission(
            initial_total=Decimal("10.00"),
            retest_total=Decimal("20.00"),
            final_total=Decimal("30.00"),
        ),
    )
    updated = service.update_admission(
        created.id,
        AdmissionRecordUpdate(retest_total=Decimal("21.50")),
    )
    assert updated.retest_total == Decimal("21.50")
    assert updated.initial_total == Decimal("10.00")
    assert updated.final_total == Decimal("30.00")
    assert updated.admission_year == 2025
    assert updated.admission_catalog_id is None


def test_patch_admission_explicit_null_score_clears_score(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Null Score")
    created = service.create_admission(
        teacher_id,
        _admission(
            initial_total=Decimal("12.50"),
            retest_total=Decimal("20.00"),
            final_total=Decimal("30.00"),
        ),
    )
    updated = service.update_admission(
        created.id,
        AdmissionRecordUpdate(initial_total=None),
    )
    assert updated.initial_total is None
    assert updated.retest_total == Decimal("20.00")
    assert updated.final_total == Decimal("30.00")


def test_patch_admission_explicit_null_catalog_unlinks(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Unlink Catalog")
    created = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2027,
            admission_catalog_id=CATALOG_2027_ID,
            initial_total=Decimal("11.00"),
        ),
    )
    updated = service.update_admission(
        created.id,
        AdmissionRecordUpdate(admission_catalog_id=None),
    )
    assert updated.admission_catalog_id is None
    assert updated.admission_year == 2027
    assert updated.study_mode == "full_time"
    assert updated.school.id == SCHOOL_A_ID
    assert updated.college.id == COLLEGE_A_ID
    assert updated.major.id == MAJOR_A_ID
    assert updated.initial_total == Decimal("11.00")


def test_patch_admission_empty_patch_is_rejected(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Empty Admission")
    created = service.create_admission(
        teacher_id,
        _admission(initial_total=Decimal("3.00")),
    )
    with pytest.raises(EmptyPatchError) as exc:
        service.update_admission(created.id, AdmissionRecordUpdate())
    assert exc.value.code == "empty_patch"
    kept = service.get_teacher(teacher_id).admission_records[0]
    assert kept.initial_total == Decimal("3.00")
    assert kept.admission_year == 2025


def test_patch_admission_changed_master_ref_must_exist_same_school_and_active(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Change Ref")
    created = service.create_admission(teacher_id, _admission())
    moved_college = service.update_admission(
        created.id,
        AdmissionRecordUpdate(college_id=COLLEGE_B_ID),
    )
    assert moved_college.school.id == SCHOOL_A_ID
    assert moved_college.college.id == COLLEGE_B_ID
    assert moved_college.major.id == MAJOR_A_ID

    with pytest.raises(InvalidReferenceError) as missing:
        service.update_admission(
            created.id,
            AdmissionRecordUpdate(major_id=9_999_993),
        )
    assert missing.value.code == "invalid_reference"
    assert "major" in missing.value.message

    with pytest.raises(InactiveReferenceError) as inactive:
        service.update_admission(
            created.id,
            AdmissionRecordUpdate(college_id=COLLEGE_INACTIVE_ID),
        )
    assert inactive.value.code == "inactive_reference"
    assert inactive.value.resource == "college"

    kept = service.get_teacher(teacher_id).admission_records[0]
    assert kept.school.id == SCHOOL_A_ID
    assert kept.college.id == COLLEGE_B_ID
    assert kept.major.id == MAJOR_A_ID

    moved_school = service.update_admission(
        created.id,
        AdmissionRecordUpdate(
            school_id=SCHOOL_C_ID,
            college_id=COLLEGE_C_ID,
            major_id=MAJOR_C_ID,
        ),
    )
    assert moved_school.school.id == SCHOOL_C_ID
    assert moved_school.college.id == COLLEGE_C_ID
    assert moved_school.major.id == MAJOR_C_ID
    assert moved_school.admission_year == 2025


def test_patch_admission_allows_score_when_master_refs_later_inactive(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Historic Ref")
    created = service.create_admission(
        teacher_id,
        _admission(initial_total=Decimal("5.00")),
    )
    for model, row_id in (
        (School, SCHOOL_A_ID),
        (College, COLLEGE_A_ID),
        (Major, MAJOR_A_ID),
    ):
        row = seeded_session.get(model, row_id)
        assert row is not None
        row.is_active = False
    seeded_session.flush()
    updated = service.update_admission(
        created.id,
        AdmissionRecordUpdate(
            initial_total=Decimal("15.00"),
            admission_year=2024,
        ),
    )
    assert updated.initial_total == Decimal("15.00")
    assert updated.admission_year == 2024
    assert updated.school.id == SCHOOL_A_ID
    assert updated.school.is_active is False
    assert updated.college.id == COLLEGE_A_ID
    assert updated.college.is_active is False
    assert updated.major.id == MAJOR_A_ID
    assert updated.major.is_active is False


def test_patch_admission_effective_state_rejects_cross_school_major(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Effective Scope")
    created = service.create_admission(teacher_id, _admission())
    with pytest.raises(ScopeMismatchError) as exc:
        service.update_admission(
            created.id,
            AdmissionRecordUpdate(major_id=MAJOR_C_ID),
        )
    assert exc.value.code == "reference_scope_mismatch"
    assert "major" in exc.value.message
    kept = service.get_teacher(teacher_id).admission_records[0]
    assert kept.school.id == SCHOOL_A_ID
    assert kept.college.id == COLLEGE_A_ID
    assert kept.major.id == MAJOR_A_ID


def test_patch_admission_catalog_identity_uses_effective_target(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Effective Catalog")
    created = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2026,
            admission_catalog_id=CATALOG_2026_FT_ID,
        ),
    )
    matched = service.update_admission(
        created.id,
        AdmissionRecordUpdate(
            admission_year=2027,
            admission_catalog_id=CATALOG_2027_ID,
        ),
    )
    assert matched.admission_year == 2027
    assert matched.admission_catalog_id == CATALOG_2027_ID
    assert matched.study_mode == "full_time"
    assert matched.school.id == SCHOOL_A_ID
    assert matched.major.id == MAJOR_A_ID

    with pytest.raises(CatalogIdentityMismatchError) as exc:
        service.update_admission(
            created.id,
            AdmissionRecordUpdate(admission_year=2026),
        )
    assert exc.value.code == "catalog_identity_mismatch"
    kept = service.get_teacher(teacher_id).admission_records[0]
    assert kept.admission_year == 2027
    assert kept.admission_catalog_id == CATALOG_2027_ID
    assert kept.study_mode == "full_time"


def test_patch_admission_duplicate_active_row(seeded_session: Session) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Duplicate Active")
    service.create_admission(teacher_id, _admission(admission_year=2021))
    second = service.create_admission(
        teacher_id,
        _admission(admission_year=2022),
    )
    nested = seeded_session.begin_nested()
    with pytest.raises(ConflictError) as exc:
        service.update_admission(
            second.id,
            AdmissionRecordUpdate(admission_year=2021),
        )
    assert exc.value.code == "duplicate_admission"
    nested.rollback()
    seeded_session.expire_all()
    years = sorted(
        row.admission_year
        for row in service.get_teacher(teacher_id).admission_records
    )
    assert years == [2021, 2022]


def test_patch_admission_duplicate_inactive_row(seeded_session: Session) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Duplicate Inactive")
    first = service.create_admission(
        teacher_id,
        _admission(admission_year=2021),
    )
    second = service.create_admission(
        teacher_id,
        _admission(admission_year=2022),
    )
    stored = AdminTeacherRepository(seeded_session).get_admission(first.id)
    assert stored is not None
    stored.is_active = False
    seeded_session.flush()
    nested = seeded_session.begin_nested()
    with pytest.raises(ConflictError) as exc:
        service.update_admission(
            second.id,
            AdmissionRecordUpdate(admission_year=2021),
        )
    assert exc.value.code == "duplicate_admission"
    nested.rollback()
    seeded_session.expire_all()
    records = {
        row.admission_year: row
        for row in service.get_teacher(teacher_id).admission_records
    }
    assert records[2021].is_active is False
    assert records[2022].is_active is True
    assert records[2022].admission_year == 2022


def test_patch_admission_allowed_when_teacher_inactive(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Patch Inactive")
    created = service.create_admission(
        teacher_id,
        _admission(initial_total=Decimal("5.00")),
    )
    service.set_teacher_status(teacher_id, False)
    updated = service.update_admission(
        created.id,
        AdmissionRecordUpdate(final_total=Decimal("9.00")),
    )
    assert updated.final_total == Decimal("9.00")
    assert updated.initial_total == Decimal("5.00")
    assert updated.school.id == SCHOOL_A_ID
    teacher = service.get_teacher(teacher_id)
    assert teacher.is_active is False
    assert teacher.admission_records[0].final_total == Decimal("9.00")


def test_set_admission_status_deactivates_active_record(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Off")
    created = service.create_admission(
        teacher_id,
        _admission(initial_total=Decimal("18.00")),
    )
    assert created.is_active is True
    updated = service.set_admission_status(created.id, False)
    assert updated.id == created.id
    assert updated.is_active is False
    assert updated.initial_total == Decimal("18.00")
    assert updated.school.id == SCHOOL_A_ID
    assert updated.college.id == COLLEGE_A_ID
    assert updated.major.id == MAJOR_A_ID
    assert service.get_teacher(teacher_id).admission_records[0].is_active is False


def test_set_admission_status_false_is_idempotent_when_inactive(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Off Again")
    created = service.create_admission(teacher_id, _admission())
    service.set_admission_status(created.id, False)
    updated = service.set_admission_status(created.id, False)
    assert updated.is_active is False
    assert updated.admission_year == 2025
    assert updated.study_mode == "full_time"
    assert updated.school.id == SCHOOL_A_ID
    assert updated.college.id == COLLEGE_A_ID
    assert updated.major.id == MAJOR_A_ID


def test_set_admission_status_reactivates_matching_refs_and_catalog(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status On")
    created = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2027,
            admission_catalog_id=CATALOG_2027_ID,
        ),
    )
    service.set_admission_status(created.id, False)
    updated = service.set_admission_status(created.id, True)
    assert updated.is_active is True
    assert updated.admission_catalog_id == CATALOG_2027_ID
    assert updated.admission_year == 2027
    assert updated.study_mode == "full_time"
    assert updated.school.id == SCHOOL_A_ID
    assert updated.school.is_active is True
    assert updated.college.id == COLLEGE_A_ID
    assert updated.college.is_active is True
    assert updated.major.id == MAJOR_A_ID
    assert updated.major.is_active is True


def test_set_admission_status_true_revalidates_when_already_active(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Still Active")
    created = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2026,
            admission_catalog_id=CATALOG_2026_FT_ID,
            initial_total=Decimal("6.00"),
        ),
    )
    assert created.is_active is True
    master_modes: list[set[str]] = []
    catalog_ids: list[int | None] = []
    original_master = AdminTeacherService._validate_master_refs
    original_catalog = AdminTeacherService._validate_catalog

    def spy_master(
        self: AdminTeacherService,
        target: object,
        *,
        active_resources: set[str],
    ) -> None:
        master_modes.append(set(active_resources))
        original_master(
            self,
            target,  # type: ignore[arg-type]
            active_resources=active_resources,
        )

    def spy_catalog(self: AdminTeacherService, target: object) -> None:
        catalog_ids.append(target.admission_catalog_id)  # type: ignore[attr-defined]
        original_catalog(self, target)  # type: ignore[arg-type]

    monkeypatch.setattr(AdminTeacherService, "_validate_master_refs", spy_master)
    monkeypatch.setattr(AdminTeacherService, "_validate_catalog", spy_catalog)
    updated = service.set_admission_status(created.id, True)
    assert updated.is_active is True
    assert updated.admission_catalog_id == CATALOG_2026_FT_ID
    assert updated.admission_year == 2026
    assert updated.study_mode == "full_time"
    assert updated.initial_total == Decimal("6.00")
    assert master_modes == [set()]
    assert catalog_ids == [CATALOG_2026_FT_ID]
    assert service.get_teacher(teacher_id).admission_records[0].is_active is True


def test_set_admission_status_reactivate_allows_later_inactive_master_refs(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Historic Ref")
    created = service.create_admission(teacher_id, _admission())
    service.set_admission_status(created.id, False)
    for model, row_id in (
        (School, SCHOOL_A_ID),
        (College, COLLEGE_A_ID),
        (Major, MAJOR_A_ID),
    ):
        row = seeded_session.get(model, row_id)
        assert row is not None
        row.is_active = False
    seeded_session.flush()
    updated = service.set_admission_status(created.id, True)
    assert updated.is_active is True
    assert updated.school.id == SCHOOL_A_ID
    assert updated.school.is_active is False
    assert updated.college.id == COLLEGE_A_ID
    assert updated.college.is_active is False
    assert updated.major.id == MAJOR_A_ID
    assert updated.major.is_active is False


def test_set_admission_status_reactivate_allows_later_inactive_catalog(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Historic Catalog")
    created = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2027,
            admission_catalog_id=CATALOG_2027_ID,
        ),
    )
    service.set_admission_status(created.id, False)
    catalog = seeded_session.get(AdmissionCatalog, CATALOG_2027_ID)
    assert catalog is not None
    catalog.is_active = False
    seeded_session.flush()
    updated = service.set_admission_status(created.id, True)
    assert updated.is_active is True
    assert updated.admission_catalog_id == CATALOG_2027_ID
    assert updated.admission_year == 2027
    assert updated.study_mode == "full_time"
    assert updated.school.id == SCHOOL_A_ID
    assert updated.college.id == COLLEGE_A_ID
    assert updated.major.id == MAJOR_A_ID
    assert catalog.is_active is False


def test_set_admission_status_reactivate_rejects_cross_school_scope(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # fk_admission_records_college_school and fk_admission_records_major_school
    # reject a stored row whose college or major belongs to another school.
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Scope")
    created = service.create_admission(teacher_id, _admission())
    service.set_admission_status(created.id, False)
    original_get_college = AdminSchoolRepository.get_college

    def other_school_college(
        self: AdminSchoolRepository,
        college_id: int,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            id=college_id,
            school_id=SCHOOL_C_ID,
            is_active=True,
        )

    monkeypatch.setattr(
        AdminSchoolRepository,
        "get_college",
        other_school_college,
    )
    with pytest.raises(ScopeMismatchError) as college_exc:
        service.set_admission_status(created.id, True)
    assert college_exc.value.code == "reference_scope_mismatch"
    assert "college" in college_exc.value.message
    monkeypatch.setattr(
        AdminSchoolRepository,
        "get_college",
        original_get_college,
    )

    def other_school_major(
        self: AdminSchoolRepository,
        major_id: int,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            id=major_id,
            school_id=SCHOOL_C_ID,
            is_active=True,
        )

    monkeypatch.setattr(AdminSchoolRepository, "get_major", other_school_major)
    with pytest.raises(ScopeMismatchError) as major_exc:
        service.set_admission_status(created.id, True)
    assert major_exc.value.code == "reference_scope_mismatch"
    assert "major" in major_exc.value.message
    stored = AdminTeacherRepository(seeded_session).get_admission(created.id)
    assert stored is not None
    assert stored.is_active is False
    assert stored.school_id == SCHOOL_A_ID
    assert stored.college_id == COLLEGE_A_ID
    assert stored.major_id == MAJOR_A_ID
    assert service.get_teacher(teacher_id).admission_records[0].is_active is False


def test_set_admission_status_reactivate_rejects_catalog_identity_mismatch(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Catalog Mismatch")
    created = service.create_admission(
        teacher_id,
        _admission(
            admission_year=2026,
            admission_catalog_id=CATALOG_2026_FT_ID,
        ),
    )
    service.set_admission_status(created.id, False)
    stored = AdminTeacherRepository(seeded_session).get_admission(created.id)
    assert stored is not None
    stored.admission_year = 2024
    seeded_session.flush()
    with pytest.raises(CatalogIdentityMismatchError) as exc:
        service.set_admission_status(created.id, True)
    assert exc.value.code == "catalog_identity_mismatch"
    kept = service.get_teacher(teacher_id).admission_records[0]
    assert kept.is_active is False
    assert kept.admission_year == 2024
    assert kept.admission_catalog_id == CATALOG_2026_FT_ID
    assert kept.study_mode == "full_time"
    assert kept.school.id == SCHOOL_A_ID
    assert kept.college.id == COLLEGE_A_ID
    assert kept.major.id == MAJOR_A_ID


def test_set_admission_status_allowed_when_teacher_inactive(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Status Inactive Teacher")
    created = service.create_admission(teacher_id, _admission())
    service.set_teacher_status(teacher_id, False)
    deactivated = service.set_admission_status(created.id, False)
    assert deactivated.is_active is False
    reactivated = service.set_admission_status(created.id, True)
    assert reactivated.is_active is True
    assert reactivated.school.id == SCHOOL_A_ID
    assert reactivated.college.id == COLLEGE_A_ID
    assert reactivated.major.id == MAJOR_A_ID
    teacher = service.get_teacher(teacher_id)
    assert teacher.is_active is False
    assert teacher.admission_records[0].is_active is True


def test_set_admission_status_missing_admission_is_not_found(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    missing_id = 9_999_994
    with pytest.raises(NotFoundError) as exc:
        service.set_admission_status(missing_id, False)
    assert exc.value.code == "not_found"
    assert exc.value.resource == "admission_record"
    assert exc.value.resource_id == missing_id


def test_replace_teach_subjects_replaces_set_and_keeps_admissions(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Subjects Replace")
    admission = service.create_admission(teacher_id, _admission())
    _put(
        service,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    detail = _put(
        service,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_ALT_ID],
    )
    assert isinstance(detail, TeacherAdminDetail)
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_ALT_ID],
        detail,
    )
    assert [row.id for row in detail.admission_records] == [admission.id]
    assert detail.admission_records[0].school.id == SCHOOL_A_ID
    assert detail.admission_records[0].admission_year == 2025


def test_replace_teach_subjects_clears_set(seeded_session: Session) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Clear",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    detail = _put(service, teacher_id, [])
    assert isinstance(detail, TeacherAdminDetail)
    _assert_subject_set(seeded_session, teacher_id, [], detail)


def test_replace_teach_subjects_same_set_is_idempotent(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Same",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    detail = _put(
        service,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    assert isinstance(detail, TeacherAdminDetail)
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        detail,
    )


def test_replace_teach_subjects_inactive_teacher_can_remove_one(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Inactive Remove",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        active=False,
    )
    detail = _put(service, teacher_id, [SUBJECT_NATIONAL_ID])
    assert isinstance(detail, TeacherAdminDetail)
    assert detail.is_active is False
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID],
        detail,
    )


def test_replace_teach_subjects_inactive_teacher_can_clear(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Inactive Clear",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        active=False,
    )
    detail = _put(service, teacher_id, [])
    assert isinstance(detail, TeacherAdminDetail)
    assert detail.is_active is False
    _assert_subject_set(seeded_session, teacher_id, [], detail)


def test_replace_teach_subjects_inactive_teacher_can_keep_same_set(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Inactive Same",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        active=False,
    )
    detail = _put(
        service,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    assert isinstance(detail, TeacherAdminDetail)
    assert detail.is_active is False
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        detail,
    )


def test_replace_teach_subjects_inactive_teacher_cannot_add_active_subject(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Inactive Add",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        active=False,
    )
    with pytest.raises(ParentInactiveError) as exc:
        _put(
            service,
            teacher_id,
            [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID, SUBJECT_ALT_ID],
        )
    assert exc.value.code == "parent_inactive"
    assert exc.value.resource == "teacher_profile"
    assert exc.value.resource_id == teacher_id
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    assert SUBJECT_ALT_ID not in _subject_ids(seeded_session, teacher_id)


def test_replace_teach_subjects_inactive_teacher_replace_with_add_keeps_old_set(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Inactive Swap",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        active=False,
    )
    with pytest.raises(ParentInactiveError) as exc:
        _put(
            service,
            teacher_id,
            [SUBJECT_NATIONAL_ID, SUBJECT_ALT_ID],
        )
    assert exc.value.code == "parent_inactive"
    assert exc.value.resource == "teacher_profile"
    linked = _subject_ids(seeded_session, teacher_id)
    assert SUBJECT_NATIONAL_ID in linked
    assert SUBJECT_SCHOOL_ID in linked
    assert SUBJECT_ALT_ID not in linked
    assert linked == sorted([SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID])


def test_replace_teach_subjects_inactive_teacher_cannot_readd_removed_subject(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Inactive Readd",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        active=False,
    )
    removed = _put(service, teacher_id, [SUBJECT_NATIONAL_ID])
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID],
        removed,
    )
    with pytest.raises(ParentInactiveError) as exc:
        _put(
            service,
            teacher_id,
            [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        )
    assert exc.value.code == "parent_inactive"
    assert exc.value.resource == "teacher_profile"
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID],
    )


def test_replace_teach_subjects_keeps_existing_subject_that_later_inactive(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Keep Inactive",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    subject = seeded_session.get(ExamSubject, SUBJECT_SCHOOL_ID)
    assert subject is not None
    subject.is_active = False
    seeded_session.flush()
    detail = _put(
        service,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        detail,
    )
    kept = {
        item.id: item.is_active for item in detail.teach_subjects
    }
    assert kept[SUBJECT_SCHOOL_ID] is False
    assert kept[SUBJECT_NATIONAL_ID] is True


def test_replace_teach_subjects_can_remove_existing_inactive_subject(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Drop Inactive",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    subject = seeded_session.get(ExamSubject, SUBJECT_SCHOOL_ID)
    assert subject is not None
    subject.is_active = False
    seeded_session.flush()
    detail = _put(service, teacher_id, [SUBJECT_NATIONAL_ID])
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID],
        detail,
    )


def test_replace_teach_subjects_rejects_added_inactive_subject(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Add Inactive",
        [SUBJECT_NATIONAL_ID],
    )
    with pytest.raises(InactiveReferenceError) as exc:
        _put(
            service,
            teacher_id,
            [SUBJECT_NATIONAL_ID, SUBJECT_INACTIVE_ID],
        )
    assert exc.value.code == "inactive_reference"
    assert exc.value.resource == "exam_subject"
    assert exc.value.resource_id == SUBJECT_INACTIVE_ID
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID],
    )


def test_replace_teach_subjects_rejects_missing_subject(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Missing",
        [SUBJECT_NATIONAL_ID],
    )
    missing_id = 9_999_995
    with pytest.raises(InvalidReferenceError) as exc:
        _put(service, teacher_id, [SUBJECT_NATIONAL_ID, missing_id])
    assert exc.value.code == "invalid_reference"
    assert "exam_subject" in exc.value.message
    assert str(missing_id) in exc.value.message
    _assert_subject_set(
        seeded_session,
        teacher_id,
        [SUBJECT_NATIONAL_ID],
    )


def test_replace_teach_subjects_validation_precedence(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    missing_teacher = _seed_subjects(
        service,
        "Subjects Precedence Missing",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
        active=False,
    )
    missing_id = 9_999_996
    with pytest.raises(InvalidReferenceError) as missing_exc:
        _put(service, missing_teacher, [SUBJECT_NATIONAL_ID, missing_id])
    assert missing_exc.value.code == "invalid_reference"
    assert str(missing_id) in missing_exc.value.message
    _assert_subject_set(
        seeded_session,
        missing_teacher,
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )

    inactive_subject_teacher = _seed_subjects(
        service,
        "Subjects Precedence Inactive",
        [SUBJECT_NATIONAL_ID],
        active=False,
    )
    with pytest.raises(ParentInactiveError) as parent_exc:
        _put(
            service,
            inactive_subject_teacher,
            [SUBJECT_NATIONAL_ID, SUBJECT_INACTIVE_ID],
        )
    assert parent_exc.value.code == "parent_inactive"
    assert parent_exc.value.resource == "teacher_profile"
    _assert_subject_set(
        seeded_session,
        inactive_subject_teacher,
        [SUBJECT_NATIONAL_ID],
    )


def test_replace_teach_subjects_missing_teacher_is_not_found(
    seeded_session: Session,
) -> None:
    service = _service(seeded_session)
    missing_id = 9_999_997
    with pytest.raises(NotFoundError) as exc:
        _put(service, missing_id, [SUBJECT_NATIONAL_ID])
    assert exc.value.code == "not_found"
    assert exc.value.resource == "teacher_profile"
    assert exc.value.resource_id == missing_id
    assert _subject_ids(seeded_session, missing_id) == []


class _ConstraintOrig(Exception):
    def __init__(self, constraint_name: str) -> None:
        super().__init__(constraint_name)
        self.diag = SimpleNamespace(constraint_name=constraint_name)


def _integrity(constraint_name: str) -> IntegrityError:
    return IntegrityError("INSERT", {}, _ConstraintOrig(constraint_name))


def _fail_flush(
    monkeypatch: pytest.MonkeyPatch,
    constraint_name: str,
) -> IntegrityError:
    original = _integrity(constraint_name)

    def boom(self: AdminTeacherRepository) -> None:
        raise original

    monkeypatch.setattr(AdminTeacherRepository, "flush", boom)
    return original


def test_replace_teach_subjects_rolls_back_flushed_delete(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _seed_subjects(
        service,
        "Subjects Rollback",
        [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID],
    )
    # Release the setup savepoint. The outer connection transaction stays open,
    # so rolling back the replace savepoint restores this set.
    seeded_session.commit()
    real_delete = AdminTeacherRepository.delete_teach_subjects_for_teacher
    real_flush = AdminTeacherRepository.flush
    phases: list[str] = []

    def delete_and_flush(
        self: AdminTeacherRepository,
        teacher_profile_id: int,
    ) -> None:
        real_delete(self, teacher_profile_id)
        self.flush()

    def flaky_flush(self: AdminTeacherRepository) -> None:
        if not phases:
            real_flush(self)
            remaining = self._session.connection().execute(
                text(
                    "SELECT exam_subject_id FROM teacher_teach_subjects "
                    "WHERE teacher_profile_id = :teacher_id "
                    "ORDER BY exam_subject_id"
                ),
                {"teacher_id": teacher_id},
            )
            assert remaining.scalars().all() == []
            phases.append("delete-flushed")
            return
        phases.append("insert-flush")
        raise RuntimeError("insert flush failed")

    monkeypatch.setattr(
        AdminTeacherRepository,
        "delete_teach_subjects_for_teacher",
        delete_and_flush,
    )
    monkeypatch.setattr(AdminTeacherRepository, "flush", flaky_flush)
    with pytest.raises(RuntimeError, match="insert flush failed"):
        _put(
            service,
            teacher_id,
            [SUBJECT_NATIONAL_ID, SUBJECT_ALT_ID],
        )
    assert phases == ["delete-flushed", "insert-flush"]
    seeded_session.rollback()
    connection = seeded_session.connection()
    seeded_session.close()
    fresh = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        assert fresh is not seeded_session
        assert _subject_ids(fresh, teacher_id) == sorted(
            [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]
        )
    finally:
        fresh.close()


def test_integrity_maps_duplicate_admission(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Map Duplicate Admission")
    _fail_flush(monkeypatch, "uq_admission_records_teacher_offering")
    with pytest.raises(ConflictError) as exc:
        service.set_teacher_status(teacher_id, False)
    assert exc.value.code == "duplicate_admission"


def test_integrity_maps_duplicate_teach_subject(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Map Duplicate Subject")
    _fail_flush(monkeypatch, "uq_teacher_teach_subjects_teacher_subject")
    with pytest.raises(ConflictError) as exc:
        service.set_teacher_status(teacher_id, False)
    assert exc.value.code == "duplicate_teach_subject"


def test_integrity_maps_admission_catalog_fk(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Map Admission Fk")
    _fail_flush(monkeypatch, "fk_admission_records_catalog_id")
    with pytest.raises(InvalidReferenceError) as exc:
        service.set_teacher_status(teacher_id, False)
    assert exc.value.code == "invalid_reference"


def test_integrity_maps_teach_subject_fk(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Map Subject Fk")
    _fail_flush(monkeypatch, "fk_teacher_teach_subjects_exam_subject_id")
    with pytest.raises(InvalidReferenceError) as exc:
        service.set_teacher_status(teacher_id, False)
    assert exc.value.code == "invalid_reference"


def test_integrity_maps_admission_year_check(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Map Year Check")
    _fail_flush(monkeypatch, "ck_admission_records_year")
    with pytest.raises(CheckViolationError) as exc:
        service.set_teacher_status(teacher_id, False)
    assert exc.value.code == "check_violation"


def test_integrity_unknown_constraint_is_reraised(
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(seeded_session)
    teacher_id = _teacher(service, "Map Unknown Constraint")
    original = _fail_flush(monkeypatch, "some_unknown_constraint")
    with pytest.raises(IntegrityError) as exc:
        service.set_teacher_status(teacher_id, False)
    assert exc.value is original
