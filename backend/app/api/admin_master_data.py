from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db, get_write_db
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
    StatusUpdate,
)
from app.services.admin_master_data import (
    AdminMasterDataService,
    CheckViolationError,
    ConflictError,
    EmptyPatchError,
    InvalidReferenceError,
    MasterDataWriteError,
    NotFoundError,
    ParentInactiveError,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-master-data"])

_HTTP_STATUS: dict[type[MasterDataWriteError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ParentInactiveError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidReferenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CheckViolationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    EmptyPatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def get_admin_read_service(
    session: Annotated[Session, Depends(get_db)],
) -> AdminMasterDataService:
    return AdminMasterDataService(AdminSchoolRepository(session))


def get_admin_write_service(
    session: Annotated[Session, Depends(get_write_db, scope="function")],
) -> AdminMasterDataService:
    return AdminMasterDataService(AdminSchoolRepository(session))


ReadServiceDep = Annotated[AdminMasterDataService, Depends(get_admin_read_service)]
WriteServiceDep = Annotated[AdminMasterDataService, Depends(get_admin_write_service)]
SchoolIdPath = Annotated[int, Path(gt=0)]
CollegeIdPath = Annotated[int, Path(gt=0)]
MajorIdPath = Annotated[int, Path(gt=0)]
ExamSubjectIdPath = Annotated[int, Path(gt=0)]
StatusQuery = Annotated[AdminStatus, Query(alias="status")]


def _call[T](action: Callable[[], T]) -> T:
    try:
        return action()
    except MasterDataWriteError as exc:
        raise HTTPException(
            status_code=_HTTP_STATUS[type(exc)],
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get("/schools", response_model=Page[SchoolAdminRead])
def list_schools(
    service: ReadServiceDep,
    q: str | None = None,
    status_filter: StatusQuery = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[SchoolAdminRead]:
    return service.list_schools(
        status=status_filter,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/schools/{school_id}", response_model=SchoolAdminRead)
def get_school(
    service: ReadServiceDep,
    school_id: SchoolIdPath,
) -> SchoolAdminRead:
    return _call(lambda: service.get_school(school_id))


@router.post(
    "/schools",
    response_model=SchoolAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_school(
    service: WriteServiceDep,
    body: SchoolCreate,
) -> SchoolAdminRead:
    return _call(lambda: service.create_school(body))


@router.patch("/schools/{school_id}", response_model=SchoolAdminRead)
def update_school(
    service: WriteServiceDep,
    school_id: SchoolIdPath,
    body: SchoolUpdate,
) -> SchoolAdminRead:
    return _call(lambda: service.update_school(school_id, body))


@router.patch("/schools/{school_id}/status", response_model=SchoolAdminRead)
def set_school_status(
    service: WriteServiceDep,
    school_id: SchoolIdPath,
    body: StatusUpdate,
) -> SchoolAdminRead:
    return _call(lambda: service.set_school_status(school_id, body.is_active))


@router.get("/schools/{school_id}/colleges", response_model=list[CollegeAdminRead])
def list_colleges(
    service: ReadServiceDep,
    school_id: SchoolIdPath,
    status_filter: StatusQuery = "all",
) -> list[CollegeAdminRead]:
    return _call(
        lambda: service.list_colleges(school_id=school_id, status=status_filter)
    )


@router.post(
    "/schools/{school_id}/colleges",
    response_model=CollegeAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_college(
    service: WriteServiceDep,
    school_id: SchoolIdPath,
    body: CollegeCreate,
) -> CollegeAdminRead:
    return _call(lambda: service.create_college(school_id, body))


@router.get("/colleges/{college_id}", response_model=CollegeAdminRead)
def get_college(
    service: ReadServiceDep,
    college_id: CollegeIdPath,
) -> CollegeAdminRead:
    return _call(lambda: service.get_college(college_id))


@router.patch("/colleges/{college_id}", response_model=CollegeAdminRead)
def update_college(
    service: WriteServiceDep,
    college_id: CollegeIdPath,
    body: CollegeUpdate,
) -> CollegeAdminRead:
    return _call(lambda: service.update_college(college_id, body))


@router.patch("/colleges/{college_id}/status", response_model=CollegeAdminRead)
def set_college_status(
    service: WriteServiceDep,
    college_id: CollegeIdPath,
    body: StatusUpdate,
) -> CollegeAdminRead:
    return _call(lambda: service.set_college_status(college_id, body.is_active))


@router.get("/schools/{school_id}/majors", response_model=list[MajorAdminRead])
def list_majors(
    service: ReadServiceDep,
    school_id: SchoolIdPath,
    status_filter: StatusQuery = "all",
) -> list[MajorAdminRead]:
    return _call(lambda: service.list_majors(school_id=school_id, status=status_filter))


@router.post(
    "/schools/{school_id}/majors",
    response_model=MajorAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_major(
    service: WriteServiceDep,
    school_id: SchoolIdPath,
    body: MajorCreate,
) -> MajorAdminRead:
    return _call(lambda: service.create_major(school_id, body))


@router.get("/majors/{major_id}", response_model=MajorAdminRead)
def get_major(
    service: ReadServiceDep,
    major_id: MajorIdPath,
) -> MajorAdminRead:
    return _call(lambda: service.get_major(major_id))


@router.patch("/majors/{major_id}", response_model=MajorAdminRead)
def update_major(
    service: WriteServiceDep,
    major_id: MajorIdPath,
    body: MajorUpdate,
) -> MajorAdminRead:
    return _call(lambda: service.update_major(major_id, body))


@router.patch("/majors/{major_id}/status", response_model=MajorAdminRead)
def set_major_status(
    service: WriteServiceDep,
    major_id: MajorIdPath,
    body: StatusUpdate,
) -> MajorAdminRead:
    return _call(lambda: service.set_major_status(major_id, body.is_active))


@router.get("/exam-subjects/national", response_model=list[ExamSubjectAdminRead])
def list_national_exam_subjects(
    service: ReadServiceDep,
    status_filter: StatusQuery = "all",
) -> list[ExamSubjectAdminRead]:
    return service.list_national_exam_subjects(status=status_filter)


@router.post(
    "/exam-subjects/national",
    response_model=ExamSubjectAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_national_exam_subject(
    service: WriteServiceDep,
    body: ExamSubjectCreate,
) -> ExamSubjectAdminRead:
    return _call(lambda: service.create_national_exam_subject(body))


@router.get(
    "/schools/{school_id}/exam-subjects",
    response_model=list[ExamSubjectAdminRead],
)
def list_school_exam_subjects(
    service: ReadServiceDep,
    school_id: SchoolIdPath,
    status_filter: StatusQuery = "all",
) -> list[ExamSubjectAdminRead]:
    return _call(
        lambda: service.list_school_exam_subjects(
            school_id=school_id,
            status=status_filter,
        )
    )


@router.post(
    "/schools/{school_id}/exam-subjects",
    response_model=ExamSubjectAdminRead,
    status_code=status.HTTP_201_CREATED,
)
def create_school_exam_subject(
    service: WriteServiceDep,
    school_id: SchoolIdPath,
    body: ExamSubjectCreate,
) -> ExamSubjectAdminRead:
    return _call(lambda: service.create_school_exam_subject(school_id, body))


@router.get("/exam-subjects/{exam_subject_id}", response_model=ExamSubjectAdminRead)
def get_exam_subject(
    service: ReadServiceDep,
    exam_subject_id: ExamSubjectIdPath,
) -> ExamSubjectAdminRead:
    return _call(lambda: service.get_exam_subject(exam_subject_id))


@router.patch("/exam-subjects/{exam_subject_id}", response_model=ExamSubjectAdminRead)
def update_exam_subject(
    service: WriteServiceDep,
    exam_subject_id: ExamSubjectIdPath,
    body: ExamSubjectUpdate,
) -> ExamSubjectAdminRead:
    return _call(lambda: service.update_exam_subject(exam_subject_id, body))


@router.patch(
    "/exam-subjects/{exam_subject_id}/status",
    response_model=ExamSubjectAdminRead,
)
def set_exam_subject_status(
    service: WriteServiceDep,
    exam_subject_id: ExamSubjectIdPath,
    body: StatusUpdate,
) -> ExamSubjectAdminRead:
    return _call(
        lambda: service.set_exam_subject_status(exam_subject_id, body.is_active)
    )
