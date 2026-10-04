from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AdmissionRecord, TeacherProfile, TeacherTeachSubject
from tests.conftest import (
    CATALOG_2026_FT_ID,
    CATALOG_SCHOOL_C_ID,
    COLLEGE_A_ID,
    COLLEGE_C_ID,
    MAJOR_A_ID,
    MAJOR_C_ID,
    SCHOOL_A_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

DISPLAY_NAME = "ZZ_S201_TEACHER"


def _add_profile(session: Session, **kwargs) -> TeacherProfile:
    values = {"display_name": DISPLAY_NAME, **kwargs}
    profile = TeacherProfile(**values)
    session.add(profile)
    session.flush()
    return profile


def _admission_kwargs(teacher_profile_id: int, **overrides) -> dict:
    values = {
        "teacher_profile_id": teacher_profile_id,
        "school_id": SCHOOL_A_ID,
        "college_id": COLLEGE_A_ID,
        "major_id": MAJOR_A_ID,
        "admission_year": 2026,
        "study_mode": "full_time",
        "admission_catalog_id": None,
    }
    values.update(overrides)
    return values


def _add_admission(
    session: Session, teacher_profile_id: int, **overrides
) -> AdmissionRecord:
    record = AdmissionRecord(**_admission_kwargs(teacher_profile_id, **overrides))
    session.add(record)
    session.flush()
    return record


def test_teacher_profile_valid_defaults(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.refresh(profile)
    assert profile.is_active is True
    assert profile.availability_status == "unknown"
    assert profile.verification_status == "unverified"


def test_invalid_availability_rejected(seeded_session: Session) -> None:
    seeded_session.add(
        TeacherProfile(display_name=DISPLAY_NAME, availability_status="paused")
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_invalid_verification_rejected(seeded_session: Session) -> None:
    seeded_session.add(
        TeacherProfile(display_name=DISPLAY_NAME, verification_status="pending")
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_admission_record_valid_without_catalog(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    record = _add_admission(seeded_session, profile.id)
    seeded_session.refresh(record)
    assert record.admission_catalog_id is None
    assert record.id is not None


def test_admission_record_decimal_scores_persist(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    record = _add_admission(
        seeded_session,
        profile.id,
        initial_total=Decimal("321.50"),
        retest_total=Decimal("85.50"),
        final_total=Decimal("410.25"),
    )
    seeded_session.refresh(record)
    assert record.initial_total == Decimal("321.50")
    assert record.retest_total == Decimal("85.50")
    assert record.final_total == Decimal("410.25")


@pytest.mark.parametrize("field", ["initial_total", "retest_total", "final_total"])
def test_negative_score_rejected(seeded_session: Session, field: str) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.add(
        AdmissionRecord(
            **_admission_kwargs(profile.id, **{field: Decimal("-0.01")})
        )
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_invalid_study_mode_rejected(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.add(
        AdmissionRecord(**_admission_kwargs(profile.id, study_mode="weekend"))
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_year_below_2000_rejected(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.add(
        AdmissionRecord(**_admission_kwargs(profile.id, admission_year=1999))
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_cross_school_college_rejected(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.add(
        AdmissionRecord(**_admission_kwargs(profile.id, college_id=COLLEGE_C_ID))
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_cross_school_major_rejected(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.add(
        AdmissionRecord(**_admission_kwargs(profile.id, major_id=MAJOR_C_ID))
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_duplicate_teacher_offering_rejected(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    _add_admission(seeded_session, profile.id)
    seeded_session.add(AdmissionRecord(**_admission_kwargs(profile.id)))
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_duplicate_teacher_offering_covers_inactive(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    record = _add_admission(seeded_session, profile.id)
    record.is_active = False
    seeded_session.flush()
    seeded_session.add(AdmissionRecord(**_admission_kwargs(profile.id)))
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_admission_record_default_is_active_true(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    record = _add_admission(seeded_session, profile.id)
    seeded_session.refresh(record)
    assert record.is_active is True


def test_admission_record_is_active_can_be_false(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    record = _add_admission(seeded_session, profile.id)
    record.is_active = False
    seeded_session.flush()
    seeded_session.refresh(record)
    assert record.is_active is False


def test_admission_record_existing_catalog_fk_ok(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    record = _add_admission(
        seeded_session,
        profile.id,
        admission_catalog_id=CATALOG_2026_FT_ID,
    )
    seeded_session.refresh(record)
    assert record.admission_catalog_id == CATALOG_2026_FT_ID


def test_catalog_five_tuple_mismatch_allowed_by_db(seeded_session: Session) -> None:
    # Service (S2-02) must reject this. Schema must not.
    profile = _add_profile(seeded_session)
    record = _add_admission(
        seeded_session,
        profile.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2026,
        study_mode="full_time",
        admission_catalog_id=CATALOG_SCHOOL_C_ID,
    )
    seeded_session.refresh(record)
    assert record.admission_catalog_id == CATALOG_SCHOOL_C_ID
    assert record.school_id == SCHOOL_A_ID


def test_teacher_teach_subject_valid(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    link = TeacherTeachSubject(
        teacher_profile_id=profile.id,
        exam_subject_id=SUBJECT_NATIONAL_ID,
    )
    seeded_session.add(link)
    seeded_session.flush()
    seeded_session.refresh(link)
    assert link.id is not None
    assert link.exam_subject_id == SUBJECT_NATIONAL_ID


def test_duplicate_teacher_subject_rejected(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.add(
        TeacherTeachSubject(
            teacher_profile_id=profile.id,
            exam_subject_id=SUBJECT_SCHOOL_ID,
        )
    )
    seeded_session.flush()
    seeded_session.add(
        TeacherTeachSubject(
            teacher_profile_id=profile.id,
            exam_subject_id=SUBJECT_SCHOOL_ID,
        )
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_missing_teacher_fk_rejected(seeded_session: Session) -> None:
    seeded_session.add(
        TeacherTeachSubject(
            teacher_profile_id=9_299_001,
            exam_subject_id=SUBJECT_NATIONAL_ID,
        )
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_missing_subject_fk_rejected(seeded_session: Session) -> None:
    profile = _add_profile(seeded_session)
    seeded_session.add(
        TeacherTeachSubject(
            teacher_profile_id=profile.id,
            exam_subject_id=9_299_002,
        )
    )
    with pytest.raises(IntegrityError):
        seeded_session.flush()
