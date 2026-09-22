from sqlalchemy.exc import IntegrityError

from app.models import (
    AdmissionCatalog,
    AdmissionCatalogDirection,
    AdmissionCatalogExamSubject,
    College,
    ExamSubject,
    Major,
    School,
)
from app.repositories.admin_catalog import AdminCatalogRepository, AdminExamOptionRow
from app.repositories.admin_master_data import AdminSchoolRepository
from app.schemas.admin_catalog import (
    CatalogAdminDetail,
    CatalogAdminSummary,
    CatalogAggregatePut,
    CatalogShellCreate,
    DirectionAdminRead,
    ExamOptionAdminRead,
    ExamUnitAdminRead,
)
from app.schemas.admin_master_data import (
    AdminStatus,
    CollegeAdminRead,
    ExamSubjectAdminRead,
    MajorAdminRead,
    Page,
    SchoolAdminRead,
)
from app.services.admin_master_data import (
    ConflictError,
    InactiveReferenceError,
    InvalidReferenceError,
    NotFoundError,
    ScopeMismatchError,
    _constraint_name,
)

CATALOG_DUPLICATE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_admission_catalogs_offering": (
        "duplicate_catalog_offering",
        "catalog offering already exists",
    ),
    "uq_admission_catalog_directions_code": (
        "duplicate_direction_code",
        "direction_code already exists on this catalog",
    ),
    "uq_catalog_exam_unit_subject": (
        "duplicate_unit_subject",
        "exam_subject already exists in this exam_unit",
    ),
    "uq_catalog_exam_unit_option_order": (
        "duplicate_option_order",
        "option_order already exists in this exam_unit",
    ),
}

CATALOG_FK_CONSTRAINTS = frozenset(
    {
        "fk_admission_catalogs_school_id",
        "fk_admission_catalogs_college_school",
        "fk_admission_catalogs_major_school",
        "fk_admission_catalog_exam_subjects_subject_id",
        "fk_admission_catalog_directions_catalog_id",
        "fk_admission_catalog_exam_subjects_catalog_id",
    }
)


def _map_catalog_integrity(exc: IntegrityError) -> Exception:
    name = _constraint_name(exc)
    if name in CATALOG_DUPLICATE_CONSTRAINTS:
        code, message = CATALOG_DUPLICATE_CONSTRAINTS[name]
        return ConflictError(code, message)
    if name in CATALOG_FK_CONSTRAINTS:
        return InvalidReferenceError()
    return exc


class AdminCatalogService:
    def __init__(
        self,
        catalogs: AdminCatalogRepository,
        masters: AdminSchoolRepository,
    ) -> None:
        self._catalogs = catalogs
        self._masters = masters

    def _flush(self) -> None:
        try:
            self._catalogs.flush()
        except IntegrityError as exc:
            mapped = _map_catalog_integrity(exc)
            if mapped is exc:
                raise
            raise mapped from exc

    def list_catalogs(
        self,
        *,
        school_id: int,
        status: AdminStatus,
        admission_year: int | None,
        college_id: int | None,
        major_id: int | None,
        study_mode: str | None,
        page: int,
        page_size: int,
    ) -> Page[CatalogAdminSummary]:
        rows, total = self._catalogs.list_catalogs(
            school_id=school_id,
            status=status,
            admission_year=admission_year,
            college_id=college_id,
            major_id=major_id,
            study_mode=study_mode,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return Page(
            items=[self._summary(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_catalog(self, catalog_id: int) -> CatalogAdminDetail:
        return self._detail(self._require_row(catalog_id))

    def create_shell(self, data: CatalogShellCreate) -> CatalogAdminDetail:
        self._validate_stable_refs(
            school_id=data.school_id,
            college_id=data.college_id,
            major_id=data.major_id,
            require_active=True,
        )
        catalog = AdmissionCatalog(
            school_id=data.school_id,
            college_id=data.college_id,
            major_id=data.major_id,
            admission_year=data.admission_year,
            study_mode=data.study_mode,
            is_active=False,
        )
        self._catalogs.add(catalog)
        self._flush()
        return self._detail(self._require_row(catalog.id))

    def replace_aggregate(
        self,
        catalog_id: int,
        data: CatalogAggregatePut,
    ) -> CatalogAdminDetail:
        catalog = self._require_catalog(catalog_id)
        self._validate_stable_refs(
            school_id=data.school_id,
            college_id=data.college_id,
            major_id=data.major_id,
            require_active=catalog.is_active,
        )
        self._validate_subjects(
            catalog_school_id=data.school_id,
            exam_units=data.exam_units,
            require_active=catalog.is_active,
        )
        catalog.school_id = data.school_id
        catalog.college_id = data.college_id
        catalog.major_id = data.major_id
        catalog.admission_year = data.admission_year
        catalog.study_mode = data.study_mode
        # Flush the new five-tuple before any child DELETE. Otherwise
        # Session.execute(delete) autoflushes it and an offering conflict
        # escapes as an unmapped IntegrityError.
        self._flush()
        self._replace_children(catalog.id, data)
        return self._detail(self._require_row(catalog.id))

    def set_status(self, catalog_id: int, is_active: bool) -> CatalogAdminDetail:
        catalog = self._require_catalog(catalog_id)
        if is_active:
            self._validate_stable_refs(
                school_id=catalog.school_id,
                college_id=catalog.college_id,
                major_id=catalog.major_id,
                require_active=True,
            )
            options = self._catalogs.list_exam_options(catalog.id)
            self._validate_loaded_subjects(
                catalog_school_id=catalog.school_id,
                subjects=[row.subject for row in options],
                require_active=True,
            )
        catalog.is_active = is_active
        self._flush()
        return self._detail(self._require_row(catalog.id))

    def _replace_children(self, catalog_id: int, data: CatalogAggregatePut) -> None:
        self._catalogs.delete_exam_options(catalog_id)
        self._catalogs.delete_directions(catalog_id)
        self._flush()
        for direction in data.directions:
            self._catalogs.add(
                AdmissionCatalogDirection(
                    admission_catalog_id=catalog_id,
                    direction_code=direction.direction_code,
                    direction_name=direction.direction_name,
                )
            )
        for unit in data.exam_units:
            for option in unit.options:
                self._catalogs.add(
                    AdmissionCatalogExamSubject(
                        admission_catalog_id=catalog_id,
                        exam_subject_id=option.exam_subject_id,
                        exam_unit=unit.exam_unit,
                        option_order=option.option_order,
                    )
                )
        self._flush()

    def _require_catalog(self, catalog_id: int) -> AdmissionCatalog:
        catalog = self._catalogs.get_catalog(catalog_id)
        if catalog is None:
            raise NotFoundError("admission_catalog", catalog_id)
        return catalog

    def _require_row(self, catalog_id: int):
        row = self._catalogs.get_catalog_row(catalog_id)
        if row is None:
            raise NotFoundError("admission_catalog", catalog_id)
        return row

    def _validate_stable_refs(
        self,
        *,
        school_id: int,
        college_id: int,
        major_id: int,
        require_active: bool,
    ) -> None:
        school = self._masters.get_school(school_id)
        if school is None:
            raise InvalidReferenceError(f"school {school_id} not found")
        college = self._masters.get_college(college_id)
        if college is None:
            raise InvalidReferenceError(f"college {college_id} not found")
        major = self._masters.get_major(major_id)
        if major is None:
            raise InvalidReferenceError(f"major {major_id} not found")
        if college.school_id != school_id:
            raise ScopeMismatchError(
                f"college {college_id} does not belong to school {school_id}"
            )
        if major.school_id != school_id:
            raise ScopeMismatchError(
                f"major {major_id} does not belong to school {school_id}"
            )
        if require_active:
            self._require_active("school", school)
            self._require_active("college", college)
            self._require_active("major", major)

    def _validate_subjects(
        self,
        *,
        catalog_school_id: int,
        exam_units: list,
        require_active: bool,
    ) -> None:
        ordered_ids: list[int] = []
        seen: set[int] = set()
        for unit in exam_units:
            for option in unit.options:
                subject_id = option.exam_subject_id
                if subject_id in seen:
                    continue
                seen.add(subject_id)
                ordered_ids.append(subject_id)
        found = self._masters.get_exam_subjects_by_ids(ordered_ids)
        by_id = {subject.id: subject for subject in found}
        subjects: list[ExamSubject] = []
        for subject_id in ordered_ids:
            subject = by_id.get(subject_id)
            if subject is None:
                raise InvalidReferenceError(f"exam_subject {subject_id} not found")
            subjects.append(subject)
        self._validate_loaded_subjects(
            catalog_school_id=catalog_school_id,
            subjects=subjects,
            require_active=require_active,
        )

    def _validate_loaded_subjects(
        self,
        *,
        catalog_school_id: int,
        subjects: list[ExamSubject],
        require_active: bool,
    ) -> None:
        for subject in subjects:
            if subject.school_id not in (None, catalog_school_id):
                raise ScopeMismatchError(
                    f"exam_subject {subject.id} does not belong to school "
                    f"{catalog_school_id}"
                )
            if require_active:
                self._require_active("exam_subject", subject)

    def _require_active(
        self,
        resource: str,
        entity: School | College | Major | ExamSubject,
    ) -> None:
        if not entity.is_active:
            raise InactiveReferenceError(resource, entity.id)

    def _summary(self, row) -> CatalogAdminSummary:
        return CatalogAdminSummary(
            id=row.catalog.id,
            admission_year=row.catalog.admission_year,
            study_mode=row.catalog.study_mode,
            is_active=row.catalog.is_active,
            school=SchoolAdminRead.model_validate(row.school),
            college=CollegeAdminRead.model_validate(row.college),
            major=MajorAdminRead.model_validate(row.major),
        )

    def _detail(self, row) -> CatalogAdminDetail:
        summary = self._summary(row)
        directions = [
            DirectionAdminRead(
                direction_code=item.direction_code,
                direction_name=item.direction_name,
            )
            for item in self._catalogs.list_directions(row.catalog.id)
        ]
        return CatalogAdminDetail(
            **summary.model_dump(),
            directions=directions,
            exam_units=self._group_exam_units(
                self._catalogs.list_exam_options(row.catalog.id)
            ),
        )

    def _group_exam_units(
        self,
        rows: list[AdminExamOptionRow],
    ) -> list[ExamUnitAdminRead]:
        grouped: dict[int, list[ExamOptionAdminRead]] = {}
        for row in rows:
            grouped.setdefault(row.link.exam_unit, []).append(
                ExamOptionAdminRead(
                    option_order=row.link.option_order,
                    subject=ExamSubjectAdminRead.model_validate(row.subject),
                )
            )
        return [
            ExamUnitAdminRead(exam_unit=unit, options=options)
            for unit, options in grouped.items()
        ]
