from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.master_data import (
    AdmissionCatalogRepository,
    SchoolRepository,
)
from app.schemas.master_data import (
    AdmissionCatalogDetail,
    AdmissionCatalogSummary,
    AdmissionYearsRead,
    CollegeSummary,
    MajorSummary,
    Page,
    SchoolSummary,
    StudyMode,
)
from app.services.master_data import MasterDataNotFoundError, MasterDataReadService

router = APIRouter(prefix="/api/v1", tags=["master-data"])


def get_master_data_read_service(
    session: Annotated[Session, Depends(get_db)],
) -> MasterDataReadService:
    return MasterDataReadService(
        SchoolRepository(session),
        AdmissionCatalogRepository(session),
    )


ServiceDep = Annotated[MasterDataReadService, Depends(get_master_data_read_service)]


def _or_404[T](action: Callable[[], T]) -> T:
    try:
        return action()
    except MasterDataNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"{exc.resource} not found",
        ) from exc


@router.get("/schools", response_model=Page[SchoolSummary])
def list_schools(
    service: ServiceDep,
    q: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[SchoolSummary]:
    return service.list_schools(q=q, page=page, page_size=page_size)


@router.get("/schools/{school_id}", response_model=SchoolSummary)
def get_school(
    service: ServiceDep,
    school_id: Annotated[int, Path(gt=0)],
) -> SchoolSummary:
    return _or_404(lambda: service.get_school(school_id))


@router.get("/schools/{school_id}/colleges", response_model=list[CollegeSummary])
def list_colleges(
    service: ServiceDep,
    school_id: Annotated[int, Path(gt=0)],
) -> list[CollegeSummary]:
    return _or_404(lambda: service.list_colleges(school_id))


@router.get("/schools/{school_id}/majors", response_model=list[MajorSummary])
def list_majors(
    service: ServiceDep,
    school_id: Annotated[int, Path(gt=0)],
) -> list[MajorSummary]:
    return _or_404(lambda: service.list_majors(school_id))


@router.get(
    "/schools/{school_id}/admission-years",
    response_model=AdmissionYearsRead,
)
def list_admission_years(
    service: ServiceDep,
    school_id: Annotated[int, Path(gt=0)],
) -> AdmissionYearsRead:
    return _or_404(lambda: service.list_admission_years(school_id))


@router.get("/admission-catalogs", response_model=Page[AdmissionCatalogSummary])
def list_catalogs(
    service: ServiceDep,
    school_id: Annotated[int, Query(gt=0)],
    admission_year: int | None = None,
    college_id: Annotated[int | None, Query(gt=0)] = None,
    major_id: Annotated[int | None, Query(gt=0)] = None,
    study_mode: StudyMode | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[AdmissionCatalogSummary]:
    return service.list_catalogs(
        school_id=school_id,
        admission_year=admission_year,
        college_id=college_id,
        major_id=major_id,
        study_mode=study_mode,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/admission-catalogs/{catalog_id}",
    response_model=AdmissionCatalogDetail,
)
def get_catalog_detail(
    service: ServiceDep,
    catalog_id: Annotated[int, Path(gt=0)],
) -> AdmissionCatalogDetail:
    return _or_404(lambda: service.get_catalog_detail(catalog_id))
