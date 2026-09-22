from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db, get_write_db
from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository
from app.schemas.admin_catalog import (
    CatalogAdminDetail,
    CatalogAdminSummary,
    CatalogAggregatePut,
    CatalogShellCreate,
    Page,
)
from app.schemas.admin_master_data import AdminStatus, StatusUpdate
from app.schemas.master_data import StudyMode
from app.services.admin_catalog import AdminCatalogService
from app.services.admin_master_data import (
    ConflictError,
    InactiveReferenceError,
    InvalidReferenceError,
    MasterDataWriteError,
    NotFoundError,
    ScopeMismatchError,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-catalog"])

_HTTP_STATUS: dict[type[MasterDataWriteError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidReferenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InactiveReferenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ScopeMismatchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def get_admin_catalog_read_service(
    session: Annotated[Session, Depends(get_db)],
) -> AdminCatalogService:
    return AdminCatalogService(
        AdminCatalogRepository(session),
        AdminSchoolRepository(session),
    )


def get_admin_catalog_write_service(
    session: Annotated[Session, Depends(get_write_db, scope="function")],
) -> AdminCatalogService:
    return AdminCatalogService(
        AdminCatalogRepository(session),
        AdminSchoolRepository(session),
    )


ReadServiceDep = Annotated[AdminCatalogService, Depends(get_admin_catalog_read_service)]
WriteServiceDep = Annotated[
    AdminCatalogService, Depends(get_admin_catalog_write_service)
]
CatalogIdPath = Annotated[int, Path(gt=0)]
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


@router.get("/admission-catalogs", response_model=Page[CatalogAdminSummary])
def list_catalogs(
    service: ReadServiceDep,
    school_id: Annotated[int, Query(gt=0)],
    status_filter: StatusQuery = "all",
    admission_year: int | None = None,
    college_id: Annotated[int | None, Query(gt=0)] = None,
    major_id: Annotated[int | None, Query(gt=0)] = None,
    study_mode: StudyMode | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[CatalogAdminSummary]:
    return service.list_catalogs(
        school_id=school_id,
        status=status_filter,
        admission_year=admission_year,
        college_id=college_id,
        major_id=major_id,
        study_mode=study_mode,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/admission-catalogs/{catalog_id}",
    response_model=CatalogAdminDetail,
)
def get_catalog(
    service: ReadServiceDep,
    catalog_id: CatalogIdPath,
) -> CatalogAdminDetail:
    return _call(lambda: service.get_catalog(catalog_id))


@router.post(
    "/admission-catalogs",
    response_model=CatalogAdminDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_catalog_shell(
    service: WriteServiceDep,
    body: CatalogShellCreate,
) -> CatalogAdminDetail:
    return _call(lambda: service.create_shell(body))


@router.put(
    "/admission-catalogs/{catalog_id}",
    response_model=CatalogAdminDetail,
)
def replace_catalog(
    service: WriteServiceDep,
    catalog_id: CatalogIdPath,
    body: CatalogAggregatePut,
) -> CatalogAdminDetail:
    return _call(lambda: service.replace_aggregate(catalog_id, body))


@router.patch(
    "/admission-catalogs/{catalog_id}/status",
    response_model=CatalogAdminDetail,
)
def set_catalog_status(
    service: WriteServiceDep,
    catalog_id: CatalogIdPath,
    body: StatusUpdate,
) -> CatalogAdminDetail:
    return _call(lambda: service.set_status(catalog_id, body.is_active))
