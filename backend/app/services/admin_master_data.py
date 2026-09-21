from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.models import College, ExamSubject, Major, School
from app.repositories.admin_master_data import AdminSchoolRepository
from app.schemas.admin_master_data import (
    AdminStatus,
    CollegeAdminRead,
    CollegeCreate,
    CollegeUpdate,
    ExamSubjectAdminRead,
    ExamSubjectCreate,
    ExamSubjectUpdate,
    MajorAdminRead,
    MajorCreate,
    MajorUpdate,
    Page,
    SchoolAdminRead,
    SchoolCreate,
    SchoolUpdate,
)

DUPLICATE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_schools_school_code": (
        "duplicate_school_code",
        "school_code already exists",
    ),
    "uq_colleges_school_college_code": (
        "duplicate_college_code",
        "college_code already exists in this school",
    ),
    "uq_majors_school_major_code": (
        "duplicate_major_code",
        "major_code already exists in this school",
    ),
    "uq_exam_subjects_national_code": (
        "duplicate_national_subject_code",
        "national subject_code already exists",
    ),
    "uq_exam_subjects_school_code": (
        "duplicate_school_subject_code",
        "subject_code already exists in this school",
    ),
}

FK_CONSTRAINTS = frozenset(
    {
        "fk_colleges_school_id",
        "fk_majors_school_id",
        "fk_exam_subjects_school_id",
    }
)


class MasterDataWriteError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundError(MasterDataWriteError):
    def __init__(self, resource: str, resource_id: int) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__("not_found", f"{resource} {resource_id} not found")


class ParentInactiveError(MasterDataWriteError):
    def __init__(self, resource: str, resource_id: int) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(
            "parent_inactive",
            f"{resource} {resource_id} is inactive",
        )


class ConflictError(MasterDataWriteError):
    pass


class InvalidReferenceError(MasterDataWriteError):
    def __init__(self, message: str = "referenced row does not exist") -> None:
        super().__init__("invalid_reference", message)


class CheckViolationError(MasterDataWriteError):
    def __init__(self, message: str = "value failed a database check") -> None:
        super().__init__("check_violation", message)


class EmptyPatchError(MasterDataWriteError):
    def __init__(self) -> None:
        super().__init__("empty_patch", "PATCH body must include at least one field")


def _constraint_name(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None
    diag = getattr(orig, "diag", None)
    if diag is not None:
        name = getattr(diag, "constraint_name", None)
        if name:
            return str(name)
    name = getattr(orig, "constraint_name", None)
    return str(name) if name else None


def _sqlstate(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None
    state = getattr(orig, "sqlstate", None)
    return str(state) if state else None


def _map_integrity_error(exc: IntegrityError) -> Exception:
    name = _constraint_name(exc)
    if name in DUPLICATE_CONSTRAINTS:
        code, message = DUPLICATE_CONSTRAINTS[name]
        return ConflictError(code, message)
    if name in FK_CONSTRAINTS or _sqlstate(exc) == "23503":
        return InvalidReferenceError()
    if _sqlstate(exc) == "23514":
        return CheckViolationError()
    return exc


class AdminMasterDataService:
    def __init__(self, repository: AdminSchoolRepository) -> None:
        self._repo = repository

    def _apply_patch(self, entity: object, data: BaseModel) -> None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            raise EmptyPatchError()
        for key, value in values.items():
            setattr(entity, key, value)

    def _flush(self) -> None:
        try:
            self._repo.flush()
        except IntegrityError as exc:
            mapped = _map_integrity_error(exc)
            if mapped is exc:
                raise
            raise mapped from exc

    def _require_school(self, school_id: int) -> School:
        school = self._repo.get_school(school_id)
        if school is None:
            raise NotFoundError("school", school_id)
        return school

    def _require_active_parent_school(self, school_id: int) -> School:
        school = self._require_school(school_id)
        if not school.is_active:
            raise ParentInactiveError("school", school_id)
        return school

    def _require_college(self, college_id: int) -> College:
        college = self._repo.get_college(college_id)
        if college is None:
            raise NotFoundError("college", college_id)
        return college

    def _require_major(self, major_id: int) -> Major:
        major = self._repo.get_major(major_id)
        if major is None:
            raise NotFoundError("major", major_id)
        return major

    def _require_exam_subject(self, exam_subject_id: int) -> ExamSubject:
        subject = self._repo.get_exam_subject(exam_subject_id)
        if subject is None:
            raise NotFoundError("exam_subject", exam_subject_id)
        return subject

    def list_schools(
        self,
        *,
        status: AdminStatus,
        q: str | None,
        page: int,
        page_size: int,
    ) -> Page[SchoolAdminRead]:
        items, total = self._repo.list_schools(
            status=status,
            q=q,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page(
            items=[SchoolAdminRead.model_validate(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_school(self, school_id: int) -> SchoolAdminRead:
        return SchoolAdminRead.model_validate(self._require_school(school_id))

    def create_school(self, data: SchoolCreate) -> SchoolAdminRead:
        school = School(
            school_code=data.school_code,
            name=data.name,
            is_active=True,
        )
        self._repo.add(school)
        self._flush()
        return SchoolAdminRead.model_validate(school)

    def update_school(self, school_id: int, data: SchoolUpdate) -> SchoolAdminRead:
        school = self._require_school(school_id)
        self._apply_patch(school, data)
        self._flush()
        return SchoolAdminRead.model_validate(school)

    def set_school_status(self, school_id: int, is_active: bool) -> SchoolAdminRead:
        school = self._require_school(school_id)
        school.is_active = is_active
        self._flush()
        return SchoolAdminRead.model_validate(school)

    def list_colleges(
        self,
        *,
        school_id: int,
        status: AdminStatus,
    ) -> list[CollegeAdminRead]:
        self._require_school(school_id)
        return [
            CollegeAdminRead.model_validate(item)
            for item in self._repo.list_colleges(school_id=school_id, status=status)
        ]

    def get_college(self, college_id: int) -> CollegeAdminRead:
        return CollegeAdminRead.model_validate(self._require_college(college_id))

    def create_college(
        self,
        school_id: int,
        data: CollegeCreate,
    ) -> CollegeAdminRead:
        self._require_active_parent_school(school_id)
        college = College(
            school_id=school_id,
            college_code=data.college_code,
            name=data.name,
            is_active=True,
        )
        self._repo.add(college)
        self._flush()
        return CollegeAdminRead.model_validate(college)

    def update_college(self, college_id: int, data: CollegeUpdate) -> CollegeAdminRead:
        college = self._require_college(college_id)
        self._apply_patch(college, data)
        self._flush()
        return CollegeAdminRead.model_validate(college)

    def set_college_status(self, college_id: int, is_active: bool) -> CollegeAdminRead:
        college = self._require_college(college_id)
        college.is_active = is_active
        self._flush()
        return CollegeAdminRead.model_validate(college)

    def list_majors(
        self,
        *,
        school_id: int,
        status: AdminStatus,
    ) -> list[MajorAdminRead]:
        self._require_school(school_id)
        return [
            MajorAdminRead.model_validate(item)
            for item in self._repo.list_majors(school_id=school_id, status=status)
        ]

    def get_major(self, major_id: int) -> MajorAdminRead:
        return MajorAdminRead.model_validate(self._require_major(major_id))

    def create_major(self, school_id: int, data: MajorCreate) -> MajorAdminRead:
        self._require_active_parent_school(school_id)
        major = Major(
            school_id=school_id,
            major_code=data.major_code,
            name=data.name,
            degree_type=data.degree_type,
            is_active=True,
        )
        self._repo.add(major)
        self._flush()
        return MajorAdminRead.model_validate(major)

    def update_major(self, major_id: int, data: MajorUpdate) -> MajorAdminRead:
        major = self._require_major(major_id)
        self._apply_patch(major, data)
        self._flush()
        return MajorAdminRead.model_validate(major)

    def set_major_status(self, major_id: int, is_active: bool) -> MajorAdminRead:
        major = self._require_major(major_id)
        major.is_active = is_active
        self._flush()
        return MajorAdminRead.model_validate(major)

    def list_national_exam_subjects(
        self,
        *,
        status: AdminStatus,
    ) -> list[ExamSubjectAdminRead]:
        return [
            ExamSubjectAdminRead.model_validate(item)
            for item in self._repo.list_national_exam_subjects(status=status)
        ]

    def list_school_exam_subjects(
        self,
        *,
        school_id: int,
        status: AdminStatus,
    ) -> list[ExamSubjectAdminRead]:
        self._require_school(school_id)
        return [
            ExamSubjectAdminRead.model_validate(item)
            for item in self._repo.list_school_exam_subjects(
                school_id=school_id,
                status=status,
            )
        ]

    def get_exam_subject(self, exam_subject_id: int) -> ExamSubjectAdminRead:
        return ExamSubjectAdminRead.model_validate(
            self._require_exam_subject(exam_subject_id)
        )

    def create_national_exam_subject(
        self,
        data: ExamSubjectCreate,
    ) -> ExamSubjectAdminRead:
        subject = ExamSubject(
            school_id=None,
            subject_code=data.subject_code,
            name=data.name,
            is_active=True,
        )
        self._repo.add(subject)
        self._flush()
        return ExamSubjectAdminRead.model_validate(subject)

    def create_school_exam_subject(
        self,
        school_id: int,
        data: ExamSubjectCreate,
    ) -> ExamSubjectAdminRead:
        self._require_active_parent_school(school_id)
        subject = ExamSubject(
            school_id=school_id,
            subject_code=data.subject_code,
            name=data.name,
            is_active=True,
        )
        self._repo.add(subject)
        self._flush()
        return ExamSubjectAdminRead.model_validate(subject)

    def update_exam_subject(
        self,
        exam_subject_id: int,
        data: ExamSubjectUpdate,
    ) -> ExamSubjectAdminRead:
        subject = self._require_exam_subject(exam_subject_id)
        self._apply_patch(subject, data)
        self._flush()
        return ExamSubjectAdminRead.model_validate(subject)

    def set_exam_subject_status(
        self,
        exam_subject_id: int,
        is_active: bool,
    ) -> ExamSubjectAdminRead:
        subject = self._require_exam_subject(exam_subject_id)
        subject.is_active = is_active
        self._flush()
        return ExamSubjectAdminRead.model_validate(subject)
