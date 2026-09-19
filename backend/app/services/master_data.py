from app.repositories.master_data import (
    AdmissionCatalogRepository,
    CatalogExamOptionRow,
    CatalogRow,
    SchoolRepository,
)
from app.schemas.master_data import (
    AdmissionCatalogDetail,
    AdmissionCatalogSummary,
    AdmissionYearsRead,
    CollegeSummary,
    DirectionRead,
    ExamSubjectOptionRead,
    ExamSubjectSummary,
    ExamUnitRead,
    MajorSummary,
    Page,
    SchoolSummary,
)


class MasterDataNotFoundError(Exception):
    def __init__(self, resource: str, resource_id: int) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} not found: {resource_id}")


class MasterDataReadService:
    def __init__(
        self,
        school_repository: SchoolRepository,
        catalog_repository: AdmissionCatalogRepository,
    ) -> None:
        self._schools = school_repository
        self._catalogs = catalog_repository

    def list_schools(
        self,
        *,
        q: str | None,
        page: int,
        page_size: int,
    ) -> Page[SchoolSummary]:
        normalized_q = _normalize_q(q)
        offset = (page - 1) * page_size
        schools, total = self._schools.list_schools(
            q=normalized_q,
            offset=offset,
            limit=page_size,
        )
        return Page(
            items=[_school_summary(school) for school in schools],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_school(self, school_id: int) -> SchoolSummary:
        return _school_summary(self._require_active_school(school_id))

    def list_colleges(self, school_id: int) -> list[CollegeSummary]:
        self._require_active_school(school_id)
        return [
            _college_summary(college)
            for college in self._schools.list_colleges(school_id)
        ]

    def list_majors(self, school_id: int) -> list[MajorSummary]:
        self._require_active_school(school_id)
        return [_major_summary(major) for major in self._schools.list_majors(school_id)]

    def list_admission_years(self, school_id: int) -> AdmissionYearsRead:
        self._require_active_school(school_id)
        return AdmissionYearsRead(
            items=self._schools.list_admission_years(school_id)
        )

    def list_catalogs(
        self,
        *,
        school_id: int,
        admission_year: int | None,
        college_id: int | None,
        major_id: int | None,
        study_mode: str | None,
        page: int,
        page_size: int,
    ) -> Page[AdmissionCatalogSummary]:
        offset = (page - 1) * page_size
        rows, total = self._catalogs.list_catalogs(
            school_id=school_id,
            admission_year=admission_year,
            college_id=college_id,
            major_id=major_id,
            study_mode=study_mode,
            offset=offset,
            limit=page_size,
        )
        return Page(
            items=[_catalog_summary(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_catalog_detail(self, catalog_id: int) -> AdmissionCatalogDetail:
        row = self._catalogs.get_catalog(catalog_id)
        if row is None:
            raise MasterDataNotFoundError("admission_catalog", catalog_id)
        directions = self._catalogs.list_directions(catalog_id)
        options = self._catalogs.list_exam_options(catalog_id)
        summary = _catalog_summary(row)
        return AdmissionCatalogDetail(
            **summary.model_dump(),
            directions=[_direction_read(item) for item in directions],
            exam_units=_group_exam_units(options),
        )

    def _require_active_school(self, school_id: int):
        school = self._schools.get_active_by_id(school_id)
        if school is None:
            raise MasterDataNotFoundError("school", school_id)
        return school


def _normalize_q(q: str | None) -> str | None:
    if q is None:
        return None
    stripped = q.strip()
    return stripped or None


def _school_summary(school) -> SchoolSummary:
    return SchoolSummary(
        id=school.id,
        school_code=school.school_code,
        name=school.name,
    )


def _college_summary(college) -> CollegeSummary:
    return CollegeSummary(
        id=college.id,
        college_code=college.college_code,
        name=college.name,
    )


def _major_summary(major) -> MajorSummary:
    return MajorSummary(
        id=major.id,
        major_code=major.major_code,
        name=major.name,
        degree_type=major.degree_type,
    )


def _exam_subject_summary(subject) -> ExamSubjectSummary:
    return ExamSubjectSummary(
        id=subject.id,
        subject_code=subject.subject_code,
        name=subject.name,
        school_id=subject.school_id,
    )


def _direction_read(direction) -> DirectionRead:
    return DirectionRead(
        id=direction.id,
        direction_code=direction.direction_code,
        direction_name=direction.direction_name,
    )


def _catalog_summary(row: CatalogRow) -> AdmissionCatalogSummary:
    return AdmissionCatalogSummary(
        id=row.catalog.id,
        admission_year=row.catalog.admission_year,
        study_mode=row.catalog.study_mode,
        school=_school_summary(row.school),
        college=_college_summary(row.college),
        major=_major_summary(row.major),
    )


def _group_exam_units(options: list[CatalogExamOptionRow]) -> list[ExamUnitRead]:
    units: list[ExamUnitRead] = []
    current_unit: int | None = None
    current_options: list[ExamSubjectOptionRead] = []
    for row in options:
        exam_unit = row.link.exam_unit
        if current_unit is not None and exam_unit != current_unit:
            units.append(
                ExamUnitRead(exam_unit=current_unit, options=current_options)
            )
            current_options = []
        current_unit = exam_unit
        current_options.append(
            ExamSubjectOptionRead(
                option_order=row.link.option_order,
                subject=_exam_subject_summary(row.subject),
            )
        )
    if current_unit is not None:
        units.append(ExamUnitRead(exam_unit=current_unit, options=current_options))
    return units
