from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db, get_write_db
from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository
from app.repositories.admin_teacher import AdminTeacherRepository
from app.schemas.admin_master_data import AdminStatus, StatusUpdate
from app.schemas.admin_teacher import (
    AdmissionRecordAdminRead,
    AdmissionRecordCreate,
    AdmissionRecordUpdate,
    AvailabilityStatus,
    AvailabilityUpdate,
    Page,
    TeacherAdminDetail,
    TeacherAdminSummary,
    TeacherCreate,
    TeacherUpdate,
    TeachSubjectsPut,
    VerificationStatus,
    VerificationUpdate,
)
from app.schemas.master_data import StudyMode
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
)
from app.services.admin_teacher import (
    AdminTeacherService,
    CatalogIdentityMismatchError,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-teacher"])

_HTTP_STATUS: dict[type[MasterDataWriteError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ParentInactiveError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidReferenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InactiveReferenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ScopeMismatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CheckViolationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EmptyPatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CatalogIdentityMismatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def get_admin_teacher_read_service(
    session: Annotated[Session, Depends(get_db)],
) -> AdminTeacherService:
    return AdminTeacherService(
        AdminTeacherRepository(session),
        AdminSchoolRepository(session),
        AdminCatalogRepository(session),
    )


def get_admin_teacher_write_service(
    session: Annotated[Session, Depends(get_write_db, scope="function")],
) -> AdminTeacherService:
    return AdminTeacherService(
        AdminTeacherRepository(session),
        AdminSchoolRepository(session),
        AdminCatalogRepository(session),
    )


ReadServiceDep = Annotated[
    AdminTeacherService, Depends(get_admin_teacher_read_service)
]
WriteServiceDep = Annotated[
    AdminTeacherService, Depends(get_admin_teacher_write_service)
]
TeacherProfileIdPath = Annotated[int, Path(gt=0)]
AdmissionRecordIdPath = Annotated[int, Path(gt=0)]
StatusQuery = Annotated[AdminStatus, Query(alias="status")]


def _call[T](action: Callable[[], T]) -> T:
    try:
        return action()
    except MasterDataWriteError as exc:
        http_status = _HTTP_STATUS.get(type(exc))
        if http_status is None:
            raise
        raise HTTPException(
            status_code=http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/teacher-profiles", response_model=Page[TeacherAdminSummary])
def list_teachers(
    service: ReadServiceDep,
    status_filter: StatusQuery = "all",
    availability: AvailabilityStatus | None = None,
    verification: VerificationStatus | None = None,
    q: str | None = None,
    school_id: Annotated[int | None, Query(gt=0)] = None,
    college_id: Annotated[int | None, Query(gt=0)] = None,
    major_id: Annotated[int | None, Query(gt=0)] = None,
    admission_year: Annotated[int | None, Query(ge=2000)] = None,
    study_mode: StudyMode | None = None,
    exam_subject_id: Annotated[int | None, Query(gt=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[TeacherAdminSummary]:
    return service.list_teachers(
        status=status_filter,
        availability=availability,
        verification=verification,
        q=q,
        school_id=school_id,
        college_id=college_id,
        major_id=major_id,
        admission_year=admission_year,
        study_mode=study_mode,
        exam_subject_id=exam_subject_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/teacher-profiles/{teacher_profile_id}",
    response_model=TeacherAdminDetail,
)
def get_teacher(
    service: ReadServiceDep,
    teacher_profile_id: TeacherProfileIdPath,
) -> TeacherAdminDetail:
    return _call(lambda: service.get_teacher(teacher_profile_id))


@router.post(
    "/teacher-profiles",
    response_model=TeacherAdminDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_teacher(
    service: WriteServiceDep,
    body: TeacherCreate,
) -> TeacherAdminDetail:
    return _call(lambda: service.create_teacher(body))


@router.patch(
    "/teacher-profiles/{teacher_profile_id}",
    response_model=TeacherAdminSummary,
)
def update_teacher(
    service: WriteServiceDep,
    teacher_profile_id: TeacherProfileIdPath,
    body: TeacherUpdate,
) -> TeacherAdminSummary:
    return _call(lambda: service.update_teacher(teacher_profile_id, body))


@router.patch(
    "/teacher-profiles/{teacher_profile_id}/status",
    response_model=TeacherAdminSummary,
)
def set_teacher_status(
    service: WriteServiceDep,
    teacher_profile_id: TeacherProfileIdPath,
    body: StatusUpdate,
) -> TeacherAdminSummary:
    return _call(
        lambda: service.set_teacher_status(teacher_profile_id, body.is_active)
    )


@router.patch(
    "/teacher-profiles/{teacher_profile_id}/availability",
    response_model=TeacherAdminSummary,
)
def set_teacher_availability(
    service: WriteServiceDep,
    teacher_profile_id: TeacherProfileIdPath,
    body: AvailabilityUpdate,
) -> TeacherAdminSummary:
    return _call(
        lambda: service.set_availability(
            teacher_profile_id,
            body.availability_status,
        )
    )


@router.patch(
    "/teacher-profiles/{teacher_profile_id}/verification",
    response_model=TeacherAdminSummary,
)
def set_teacher_verification(
    service: WriteServiceDep,
    teacher_profile_id: TeacherProfileIdPath,
    body: VerificationUpdate,
) -> TeacherAdminSummary:
    return _call(
        lambda: service.set_verification(
            teacher_profile_id,
            body.verification_status,
        )
    )


@router.post(
    "/teacher-profiles/{teacher_profile_id}/admission-records",
    response_model=AdmissionRecordAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admission(
    service: WriteServiceDep,
    teacher_profile_id: TeacherProfileIdPath,
    body: AdmissionRecordCreate,
) -> AdmissionRecordAdminRead:
    return _call(lambda: service.create_admission(teacher_profile_id, body))


@router.patch(
    "/admission-records/{admission_record_id}",
    response_model=AdmissionRecordAdminRead,
)
def update_admission(
    service: WriteServiceDep,
    admission_record_id: AdmissionRecordIdPath,
    body: AdmissionRecordUpdate,
) -> AdmissionRecordAdminRead:
    return _call(lambda: service.update_admission(admission_record_id, body))


@router.patch(
    "/admission-records/{admission_record_id}/status",
    response_model=AdmissionRecordAdminRead,
)
def set_admission_status(
    service: WriteServiceDep,
    admission_record_id: AdmissionRecordIdPath,
    body: StatusUpdate,
) -> AdmissionRecordAdminRead:
    return _call(
        lambda: service.set_admission_status(admission_record_id, body.is_active)
    )


@router.put(
    "/teacher-profiles/{teacher_profile_id}/teach-subjects",
    response_model=TeacherAdminDetail,
)
def replace_teach_subjects(
    service: WriteServiceDep,
    teacher_profile_id: TeacherProfileIdPath,
    body: TeachSubjectsPut,
) -> TeacherAdminDetail:
    return _call(lambda: service.replace_teach_subjects(teacher_profile_id, body))
