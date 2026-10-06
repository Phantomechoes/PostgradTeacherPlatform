from sqlalchemy.orm import Session

from app.models import AdmissionRecord, TeacherProfile, TeacherTeachSubject
from app.repositories.admin_teacher import AdminTeacherRepository
from tests.conftest import (
    COLLEGE_A_ID,
    COLLEGE_C_ID,
    MAJOR_A2_ID,
    MAJOR_A_ID,
    MAJOR_C_ID,
    SCHOOL_A_ID,
    SCHOOL_C_ID,
    SUBJECT_ALT_ID,
    SUBJECT_INACTIVE_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

PREFIX = "ZZS202"


def _repo(session: Session) -> AdminTeacherRepository:
    return AdminTeacherRepository(session)


def _teacher(
    session: Session,
    name: str,
    *,
    bio: str | None = None,
    is_active: bool = True,
    availability: str = "unknown",
    verification: str = "unverified",
) -> TeacherProfile:
    teacher = TeacherProfile(
        display_name=name,
        bio=bio,
        is_active=is_active,
        availability_status=availability,
        verification_status=verification,
    )
    repo = _repo(session)
    repo.add_teacher(teacher)
    repo.flush()
    return teacher


def _admission(
    session: Session,
    teacher_id: int,
    *,
    school_id: int,
    college_id: int,
    major_id: int,
    admission_year: int,
    study_mode: str,
    is_active: bool = True,
) -> AdmissionRecord:
    admission = AdmissionRecord(
        teacher_profile_id=teacher_id,
        school_id=school_id,
        college_id=college_id,
        major_id=major_id,
        admission_year=admission_year,
        study_mode=study_mode,
        admission_catalog_id=None,
        is_active=is_active,
    )
    repo = _repo(session)
    repo.add_admission(admission)
    repo.flush()
    return admission


def _link(session: Session, teacher_id: int, exam_subject_id: int) -> None:
    repo = _repo(session)
    repo.add_teach_subject(
        TeacherTeachSubject(
            teacher_profile_id=teacher_id,
            exam_subject_id=exam_subject_id,
        )
    )
    repo.flush()


def _ids(session: Session, **filters: object) -> set[int]:
    params: dict[str, object] = {
        "status": "all",
        "availability": None,
        "verification": None,
        "q": PREFIX,
        "school_id": None,
        "college_id": None,
        "major_id": None,
        "admission_year": None,
        "study_mode": None,
        "exam_subject_id": None,
        "offset": 0,
        "limit": 50,
    }
    params.update(filters)
    items, total = _repo(session).list_teachers(**params)  # type: ignore[arg-type]
    assert total == len(items) or params["limit"] != 50
    return {item.id for item in items}


def test_list_filters_status_availability_verification_and_name(
    seeded_session: Session,
) -> None:
    active = _teacher(
        seeded_session,
        f"{PREFIX} Filter Active",
        availability="available",
        verification="verified",
    )
    idle = _teacher(
        seeded_session,
        f"{PREFIX} Filter Idle",
        availability="unavailable",
        verification="rejected",
        is_active=False,
    )
    named = _teacher(
        seeded_session,
        f"{PREFIX} Filter Bio Carrier",
        bio=f"{PREFIX}BioToken",
    )

    assert _ids(seeded_session, q=f"{PREFIX} Filter", status="active") == {
        active.id,
        named.id,
    }
    assert _ids(seeded_session, q=f"{PREFIX} Filter", status="inactive") == {idle.id}
    assert _ids(
        seeded_session,
        q=f"{PREFIX} Filter",
        availability="available",
    ) == {active.id}
    assert _ids(
        seeded_session,
        q=f"{PREFIX} Filter",
        verification="verified",
    ) == {active.id}
    assert _ids(seeded_session, q=f"{PREFIX}BioToken") == set()
    assert _ids(seeded_session, q=f"{PREFIX} filter active") == {active.id}


def test_list_orders_by_display_name_then_id_and_keeps_total(
    seeded_session: Session,
) -> None:
    later = _teacher(seeded_session, f"{PREFIX} Order Z")
    first = _teacher(seeded_session, f"{PREFIX} Order M")
    second = _teacher(seeded_session, f"{PREFIX} Order M")
    page1, total1 = _repo(seeded_session).list_teachers(
        status="all",
        availability=None,
        verification=None,
        q=f"{PREFIX} Order",
        school_id=None,
        college_id=None,
        major_id=None,
        admission_year=None,
        study_mode=None,
        exam_subject_id=None,
        offset=0,
        limit=2,
    )
    page2, total2 = _repo(seeded_session).list_teachers(
        status="all",
        availability=None,
        verification=None,
        q=f"{PREFIX} Order",
        school_id=None,
        college_id=None,
        major_id=None,
        admission_year=None,
        study_mode=None,
        exam_subject_id=None,
        offset=2,
        limit=2,
    )
    assert total1 == 3
    assert total2 == 3
    assert [item.id for item in page1] == [first.id, second.id]
    assert [item.id for item in page2] == [later.id]


def test_admission_filters_use_one_active_correlated_row(
    seeded_session: Session,
) -> None:
    cross = _teacher(seeded_session, f"{PREFIX} Cross")
    _admission(
        seeded_session,
        cross.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2026,
        study_mode="full_time",
    )
    _admission(
        seeded_session,
        cross.id,
        school_id=SCHOOL_C_ID,
        college_id=COLLEGE_C_ID,
        major_id=MAJOR_C_ID,
        admission_year=2027,
        study_mode="part_time",
    )
    other = _teacher(seeded_session, f"{PREFIX} Other")
    _admission(
        seeded_session,
        other.id,
        school_id=SCHOOL_C_ID,
        college_id=COLLEGE_C_ID,
        major_id=MAJOR_C_ID,
        admission_year=2026,
        study_mode="full_time",
    )
    archived = _teacher(seeded_session, f"{PREFIX} Archived Admission")
    _admission(
        seeded_session,
        archived.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2026,
        study_mode="full_time",
        is_active=False,
    )

    assert _ids(
        seeded_session,
        school_id=SCHOOL_A_ID,
        major_id=MAJOR_C_ID,
    ) == set()
    assert _ids(
        seeded_session,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_C_ID,
    ) == set()
    assert _ids(
        seeded_session,
        school_id=SCHOOL_A_ID,
        admission_year=2027,
    ) == set()
    assert _ids(
        seeded_session,
        school_id=SCHOOL_A_ID,
        study_mode="part_time",
    ) == set()
    assert _ids(seeded_session, school_id=SCHOOL_A_ID) == {cross.id}
    assert _ids(
        seeded_session,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2026,
        study_mode="full_time",
    ) == {cross.id}
    assert _ids(
        seeded_session,
        school_id=SCHOOL_C_ID,
        admission_year=2026,
    ) == {other.id}
    assert archived.id not in _ids(seeded_session, school_id=SCHOOL_A_ID)
    assert archived.id not in _ids(seeded_session, admission_year=2026)


def test_multiple_admissions_do_not_duplicate_teacher_total(
    seeded_session: Session,
) -> None:
    teacher = _teacher(seeded_session, f"{PREFIX} Multi Admission")
    _admission(
        seeded_session,
        teacher.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2026,
        study_mode="full_time",
    )
    _admission(
        seeded_session,
        teacher.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A2_ID,
        admission_year=2027,
        study_mode="full_time",
    )
    items, total = _repo(seeded_session).list_teachers(
        status="all",
        availability=None,
        verification=None,
        q=f"{PREFIX} Multi Admission",
        school_id=SCHOOL_A_ID,
        college_id=None,
        major_id=None,
        admission_year=None,
        study_mode=None,
        exam_subject_id=None,
        offset=0,
        limit=20,
    )
    assert total == 1
    assert [item.id for item in items] == [teacher.id]


def test_exam_subject_filter_uses_teach_subject_rows_only(
    seeded_session: Session,
) -> None:
    linked = _teacher(seeded_session, f"{PREFIX} Linked Subject")
    _link(seeded_session, linked.id, SUBJECT_SCHOOL_ID)
    _link(seeded_session, linked.id, SUBJECT_INACTIVE_ID)
    _admission(
        seeded_session,
        linked.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2026,
        study_mode="full_time",
    )
    _admission(
        seeded_session,
        linked.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A2_ID,
        admission_year=2027,
        study_mode="part_time",
    )
    unlinked = _teacher(seeded_session, f"{PREFIX} Unlinked Subject")
    _admission(
        seeded_session,
        unlinked.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2026,
        study_mode="full_time",
    )

    items, total = _repo(seeded_session).list_teachers(
        status="all",
        availability=None,
        verification=None,
        q=f"{PREFIX} Linked Subject",
        school_id=SCHOOL_A_ID,
        college_id=None,
        major_id=None,
        admission_year=None,
        study_mode=None,
        exam_subject_id=SUBJECT_SCHOOL_ID,
        offset=0,
        limit=20,
    )
    assert total == 1
    assert [item.id for item in items] == [linked.id]
    assert _ids(
        seeded_session,
        q=f"{PREFIX} Linked Subject",
        exam_subject_id=SUBJECT_INACTIVE_ID,
    ) == {linked.id}
    assert _ids(
        seeded_session,
        q=f"{PREFIX} Unlinked Subject",
        exam_subject_id=SUBJECT_NATIONAL_ID,
    ) == set()
    assert _ids(
        seeded_session,
        q=f"{PREFIX} Linked Subject",
        school_id=SCHOOL_C_ID,
        exam_subject_id=SUBJECT_SCHOOL_ID,
    ) == set()
    assert _ids(
        seeded_session,
        q=f"{PREFIX} Linked Subject",
        exam_subject_id=SUBJECT_ALT_ID,
    ) == set()


def test_teachers_without_admissions_remain_listable(
    seeded_session: Session,
) -> None:
    plain = _teacher(seeded_session, f"{PREFIX} Plain")
    assert plain.id in _ids(seeded_session, q=f"{PREFIX} Plain")


def test_admission_and_teach_subject_reads_are_ordered(
    seeded_session: Session,
) -> None:
    teacher = _teacher(seeded_session, f"{PREFIX} Ordered Children")
    inactive = _admission(
        seeded_session,
        teacher.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2030,
        study_mode="full_time",
        is_active=False,
    )
    older = _admission(
        seeded_session,
        teacher.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A2_ID,
        admission_year=2026,
        study_mode="full_time",
    )
    newer_same_year = _admission(
        seeded_session,
        teacher.id,
        school_id=SCHOOL_C_ID,
        college_id=COLLEGE_C_ID,
        major_id=MAJOR_C_ID,
        admission_year=2026,
        study_mode="part_time",
    )
    newest = _admission(
        seeded_session,
        teacher.id,
        school_id=SCHOOL_A_ID,
        college_id=COLLEGE_A_ID,
        major_id=MAJOR_A_ID,
        admission_year=2029,
        study_mode="part_time",
    )
    rows = _repo(seeded_session).list_admissions_for_teacher(teacher.id)
    assert [row.admission.id for row in rows] == [
        newest.id,
        older.id,
        newer_same_year.id,
        inactive.id,
    ]
    loaded = _repo(seeded_session).get_admission_row(older.id)
    assert loaded is not None
    assert loaded.school.id == SCHOOL_A_ID
    assert loaded.college.id == COLLEGE_A_ID
    assert loaded.major.id == MAJOR_A2_ID

    _link(seeded_session, teacher.id, SUBJECT_SCHOOL_ID)
    _link(seeded_session, teacher.id, SUBJECT_NATIONAL_ID)
    subjects = _repo(seeded_session).list_teach_subjects_for_teacher(teacher.id)
    assert [row.subject.id for row in subjects] == [
        SUBJECT_NATIONAL_ID,
        SUBJECT_SCHOOL_ID,
    ]


def test_missing_teacher_and_admission_are_none(seeded_session: Session) -> None:
    repo = _repo(seeded_session)
    assert repo.get_teacher(9_999_999) is None
    assert repo.get_admission(9_999_999) is None
    assert repo.get_admission_row(9_999_999) is None
