from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.models import AdmissionRecord, ExamSubject, TeacherProfile, TeacherTeachSubject
from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository
from app.repositories.admin_teacher import AdminAdmissionRow, AdminTeacherRepository
from app.schemas.admin_master_data import (
    AdminStatus,
    CollegeAdminRead,
    ExamSubjectAdminRead,
    MajorAdminRead,
    SchoolAdminRead,
)
from app.schemas.admin_teacher import (
    AdmissionRecordAdminRead,
    AdmissionRecordCreate,
    AdmissionRecordUpdate,
    AvailabilityStatus,
    Page,
    TeacherAdminDetail,
    TeacherAdminSummary,
    TeacherCreate,
    TeacherUpdate,
    TeachSubjectsPut,
    VerificationStatus,
)
from app.services.admin_master_data import (
    CheckViolationError,
    ConflictError,
    EmptyPatchError,
    InactiveReferenceError,
    InvalidReferenceError,
    MasterDataWriteError,
    NotFoundError,
    ParentInactiveError,
    ScopeMismatchError,
    _constraint_name,
)
from app.services.master_data import _normalize_q

TEACHER_DUPLICATE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_admission_records_teacher_offering": (
        "duplicate_admission",
        "admission offering already exists for this teacher",
    ),
    "uq_teacher_teach_subjects_teacher_subject": (
        "duplicate_teach_subject",
        "teach subject already exists for this teacher",
    ),
}

TEACHER_FK_CONSTRAINTS = frozenset(
    {
        "fk_admission_records_teacher_id",
        "fk_admission_records_school_id",
        "fk_admission_records_college_school",
        "fk_admission_records_major_school",
        "fk_admission_records_catalog_id",
        "fk_teacher_teach_subjects_teacher_id",
        "fk_teacher_teach_subjects_exam_subject_id",
    }
)

TEACHER_CHECK_CONSTRAINTS = frozenset(
    {
        "ck_teacher_profiles_availability",
        "ck_teacher_profiles_verification",
        "ck_admission_records_study_mode",
        "ck_admission_records_year",
        "ck_admission_records_initial_total_nonnegative",
        "ck_admission_records_retest_total_nonnegative",
        "ck_admission_records_final_total_nonnegative",
    }
)

_MASTER_RESOURCES = frozenset({"school", "college", "major"})


class CatalogIdentityMismatchError(MasterDataWriteError):
    def __init__(self) -> None:
        super().__init__(
            "catalog_identity_mismatch",
            "admission catalog identity does not match the admission offering",
        )


def _map_teacher_integrity(exc: IntegrityError) -> Exception:
    name = _constraint_name(exc)
    if name in TEACHER_DUPLICATE_CONSTRAINTS:
        code, message = TEACHER_DUPLICATE_CONSTRAINTS[name]
        return ConflictError(code, message)
    if name in TEACHER_FK_CONSTRAINTS:
        return InvalidReferenceError()
    if name in TEACHER_CHECK_CONSTRAINTS:
        return CheckViolationError()
    return exc


@dataclass(frozen=True, slots=True)
class _AdmissionTarget:
    school_id: int
    college_id: int
    major_id: int
    admission_year: int
    study_mode: str
    admission_catalog_id: int | None
    initial_total: Decimal | None
    retest_total: Decimal | None
    final_total: Decimal | None


def _target_from_create(data: AdmissionRecordCreate) -> _AdmissionTarget:
    return _AdmissionTarget(
        school_id=data.school_id,
        college_id=data.college_id,
        major_id=data.major_id,
        admission_year=data.admission_year,
        study_mode=data.study_mode,
        admission_catalog_id=data.admission_catalog_id,
        initial_total=data.initial_total,
        retest_total=data.retest_total,
        final_total=data.final_total,
    )


def _target_from_record(admission: AdmissionRecord) -> _AdmissionTarget:
    return _AdmissionTarget(
        school_id=admission.school_id,
        college_id=admission.college_id,
        major_id=admission.major_id,
        admission_year=admission.admission_year,
        study_mode=admission.study_mode,
        admission_catalog_id=admission.admission_catalog_id,
        initial_total=admission.initial_total,
        retest_total=admission.retest_total,
        final_total=admission.final_total,
    )


def _target_from_patch(
    admission: AdmissionRecord,
    values: dict[str, Any],
) -> _AdmissionTarget:
    current = _target_from_record(admission)
    return _AdmissionTarget(
        school_id=values.get("school_id", current.school_id),
        college_id=values.get("college_id", current.college_id),
        major_id=values.get("major_id", current.major_id),
        admission_year=values.get("admission_year", current.admission_year),
        study_mode=values.get("study_mode", current.study_mode),
        admission_catalog_id=values.get(
            "admission_catalog_id",
            current.admission_catalog_id,
        ),
        initial_total=values.get("initial_total", current.initial_total),
        retest_total=values.get("retest_total", current.retest_total),
        final_total=values.get("final_total", current.final_total),
    )


def _assign_target(admission: AdmissionRecord, target: _AdmissionTarget) -> None:
    admission.school_id = target.school_id
    admission.college_id = target.college_id
    admission.major_id = target.major_id
    admission.admission_year = target.admission_year
    admission.study_mode = target.study_mode
    admission.admission_catalog_id = target.admission_catalog_id
    admission.initial_total = target.initial_total
    admission.retest_total = target.retest_total
    admission.final_total = target.final_total


def _changed_master_resources(
    admission: AdmissionRecord,
    target: _AdmissionTarget,
) -> set[str]:
    changed: set[str] = set()
    if target.school_id != admission.school_id:
        changed.add("school")
    if target.college_id != admission.college_id:
        changed.add("college")
    if target.major_id != admission.major_id:
        changed.add("major")
    return changed


class AdminTeacherService:
    def __init__(
        self,
        teachers: AdminTeacherRepository,
        masters: AdminSchoolRepository,
        catalogs: AdminCatalogRepository,
    ) -> None:
        self._teachers = teachers
        self._masters = masters
        self._catalogs = catalogs

    def _flush(self) -> None:
        try:
            self._teachers.flush()
        except IntegrityError as exc:
            mapped = _map_teacher_integrity(exc)
            if mapped is exc:
                raise
            raise mapped from exc

    def list_teachers(
        self,
        *,
        status: AdminStatus,
        availability: AvailabilityStatus | None,
        verification: VerificationStatus | None,
        q: str | None,
        school_id: int | None,
        college_id: int | None,
        major_id: int | None,
        admission_year: int | None,
        study_mode: str | None,
        exam_subject_id: int | None,
        page: int,
        page_size: int,
    ) -> Page[TeacherAdminSummary]:
        items, total = self._teachers.list_teachers(
            status=status,
            availability=availability,
            verification=verification,
            q=_normalize_q(q),
            school_id=school_id,
            college_id=college_id,
            major_id=major_id,
            admission_year=admission_year,
            study_mode=study_mode,
            exam_subject_id=exam_subject_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page(
            items=[_summary(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_teacher(self, teacher_profile_id: int) -> TeacherAdminDetail:
        return self._detail(self._require_teacher(teacher_profile_id))

    def create_teacher(self, data: TeacherCreate) -> TeacherAdminDetail:
        teacher = TeacherProfile(
            display_name=data.display_name,
            bio=data.bio,
            is_active=True,
            availability_status="unknown",
            verification_status="unverified",
        )
        self._teachers.add_teacher(teacher)
        self._flush()
        return self._detail(teacher)

    def update_teacher(
        self,
        teacher_profile_id: int,
        data: TeacherUpdate,
    ) -> TeacherAdminSummary:
        teacher = self._require_teacher(teacher_profile_id)
        values = data.model_dump(exclude_unset=True)
        if not values:
            raise EmptyPatchError()
        for key, value in values.items():
            setattr(teacher, key, value)
        self._flush()
        return _summary(teacher)

    def set_teacher_status(
        self,
        teacher_profile_id: int,
        is_active: bool,
    ) -> TeacherAdminSummary:
        teacher = self._require_teacher(teacher_profile_id)
        teacher.is_active = is_active
        self._flush()
        return _summary(teacher)

    def set_availability(
        self,
        teacher_profile_id: int,
        availability_status: AvailabilityStatus,
    ) -> TeacherAdminSummary:
        teacher = self._require_teacher(teacher_profile_id)
        teacher.availability_status = availability_status
        self._flush()
        return _summary(teacher)

    def set_verification(
        self,
        teacher_profile_id: int,
        verification_status: VerificationStatus,
    ) -> TeacherAdminSummary:
        teacher = self._require_teacher(teacher_profile_id)
        teacher.verification_status = verification_status
        self._flush()
        return _summary(teacher)

    def create_admission(
        self,
        teacher_profile_id: int,
        data: AdmissionRecordCreate,
    ) -> AdmissionRecordAdminRead:
        teacher = self._require_teacher(teacher_profile_id)
        if not teacher.is_active:
            raise ParentInactiveError("teacher_profile", teacher.id)
        target = _target_from_create(data)
        self._validate_master_refs(target, active_resources=set(_MASTER_RESOURCES))
        self._validate_catalog(target)
        admission = AdmissionRecord(
            teacher_profile_id=teacher.id,
            school_id=target.school_id,
            college_id=target.college_id,
            major_id=target.major_id,
            admission_year=target.admission_year,
            study_mode=target.study_mode,
            admission_catalog_id=target.admission_catalog_id,
            initial_total=target.initial_total,
            retest_total=target.retest_total,
            final_total=target.final_total,
            is_active=True,
        )
        self._teachers.add_admission(admission)
        self._flush()
        return self._require_admission_read(admission.id)

    def update_admission(
        self,
        admission_record_id: int,
        data: AdmissionRecordUpdate,
    ) -> AdmissionRecordAdminRead:
        admission = self._require_admission(admission_record_id)
        values = data.model_dump(exclude_unset=True)
        if not values:
            raise EmptyPatchError()
        target = _target_from_patch(admission, values)
        self._validate_master_refs(
            target,
            active_resources=_changed_master_resources(admission, target),
        )
        self._validate_catalog(target)
        _assign_target(admission, target)
        self._flush()
        return self._require_admission_read(admission.id)

    def set_admission_status(
        self,
        admission_record_id: int,
        is_active: bool,
    ) -> AdmissionRecordAdminRead:
        admission = self._require_admission(admission_record_id)
        if is_active:
            target = _target_from_record(admission)
            self._validate_master_refs(target, active_resources=set())
            self._validate_catalog(target)
        admission.is_active = is_active
        self._flush()
        return self._require_admission_read(admission.id)

    def replace_teach_subjects(
        self,
        teacher_profile_id: int,
        data: TeachSubjectsPut,
    ) -> TeacherAdminDetail:
        teacher = self._require_teacher(teacher_profile_id)
        existing_ids = {
            row.link.exam_subject_id
            for row in self._teachers.list_teach_subjects_for_teacher(teacher.id)
        }
        requested_ids = list(data.exam_subject_ids)
        subjects = self._subjects_by_id(requested_ids)
        for subject_id in requested_ids:
            if subject_id not in subjects:
                raise InvalidReferenceError(f"exam_subject {subject_id} not found")
        added_ids = [
            subject_id
            for subject_id in requested_ids
            if subject_id not in existing_ids
        ]
        # Existence, then D7, then D12. DELETE runs only after every check passes.
        if not teacher.is_active and added_ids:
            raise ParentInactiveError("teacher_profile", teacher.id)
        for subject_id in added_ids:
            subject = subjects[subject_id]
            if not subject.is_active:
                raise InactiveReferenceError("exam_subject", subject.id)
        self._teachers.delete_teach_subjects_for_teacher(teacher.id)
        for subject_id in requested_ids:
            self._teachers.add_teach_subject(
                TeacherTeachSubject(
                    teacher_profile_id=teacher.id,
                    exam_subject_id=subject_id,
                )
            )
        self._flush()
        return self._detail(teacher)

    def _require_teacher(self, teacher_profile_id: int) -> TeacherProfile:
        teacher = self._teachers.get_teacher(teacher_profile_id)
        if teacher is None:
            raise NotFoundError("teacher_profile", teacher_profile_id)
        return teacher

    def _require_admission(self, admission_record_id: int) -> AdmissionRecord:
        admission = self._teachers.get_admission(admission_record_id)
        if admission is None:
            raise NotFoundError("admission_record", admission_record_id)
        return admission

    def _require_admission_read(
        self,
        admission_record_id: int,
    ) -> AdmissionRecordAdminRead:
        row = self._teachers.get_admission_row(admission_record_id)
        if row is None:
            raise NotFoundError("admission_record", admission_record_id)
        return _admission_read(row)

    def _subjects_by_id(self, subject_ids: list[int]) -> dict[int, ExamSubject]:
        found = self._masters.get_exam_subjects_by_ids(subject_ids)
        return {subject.id: subject for subject in found}

    def _validate_master_refs(
        self,
        target: _AdmissionTarget,
        *,
        active_resources: set[str],
    ) -> None:
        school = self._masters.get_school(target.school_id)
        if school is None:
            raise InvalidReferenceError(f"school {target.school_id} not found")
        college = self._masters.get_college(target.college_id)
        if college is None:
            raise InvalidReferenceError(f"college {target.college_id} not found")
        major = self._masters.get_major(target.major_id)
        if major is None:
            raise InvalidReferenceError(f"major {target.major_id} not found")
        if college.school_id != target.school_id:
            raise ScopeMismatchError(
                f"college {target.college_id} does not belong to school "
                f"{target.school_id}"
            )
        if major.school_id != target.school_id:
            raise ScopeMismatchError(
                f"major {target.major_id} does not belong to school "
                f"{target.school_id}"
            )
        if "school" in active_resources and not school.is_active:
            raise InactiveReferenceError("school", school.id)
        if "college" in active_resources and not college.is_active:
            raise InactiveReferenceError("college", college.id)
        if "major" in active_resources and not major.is_active:
            raise InactiveReferenceError("major", major.id)

    def _validate_catalog(self, target: _AdmissionTarget) -> None:
        catalog_id = target.admission_catalog_id
        if catalog_id is None:
            return
        catalog = self._catalogs.get_catalog(catalog_id)
        if catalog is None:
            raise InvalidReferenceError(f"admission_catalog {catalog_id} not found")
        if (
            catalog.school_id != target.school_id
            or catalog.college_id != target.college_id
            or catalog.major_id != target.major_id
            or catalog.admission_year != target.admission_year
            or catalog.study_mode != target.study_mode
        ):
            raise CatalogIdentityMismatchError()

    def _detail(self, teacher: TeacherProfile) -> TeacherAdminDetail:
        summary = _summary(teacher)
        admissions = self._teachers.list_admissions_for_teacher(teacher.id)
        subjects = self._teachers.list_teach_subjects_for_teacher(teacher.id)
        return TeacherAdminDetail(
            **summary.model_dump(),
            admission_records=[_admission_read(row) for row in admissions],
            teach_subjects=[
                ExamSubjectAdminRead.model_validate(row.subject) for row in subjects
            ],
        )


def _summary(teacher: TeacherProfile) -> TeacherAdminSummary:
    return TeacherAdminSummary.model_validate(teacher)


def _admission_read(row: AdminAdmissionRow) -> AdmissionRecordAdminRead:
    admission = row.admission
    return AdmissionRecordAdminRead(
        id=admission.id,
        teacher_profile_id=admission.teacher_profile_id,
        school=SchoolAdminRead.model_validate(row.school),
        college=CollegeAdminRead.model_validate(row.college),
        major=MajorAdminRead.model_validate(row.major),
        admission_year=admission.admission_year,
        study_mode=admission.study_mode,
        admission_catalog_id=admission.admission_catalog_id,
        initial_total=admission.initial_total,
        retest_total=admission.retest_total,
        final_total=admission.final_total,
        is_active=admission.is_active,
    )
