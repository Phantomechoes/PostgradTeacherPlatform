from pathlib import Path

from sqlalchemy.orm import Session

from app.importer.load import load_document
from app.importer.preflight import preflight
from app.importer.report import ImportErrorItem, ImportReport
from app.importer.schemas import (
    CatalogImport,
    ImportDocument,
    SchoolOptionImport,
    SchoolSubjectImport,
)
from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository
from app.schemas.admin_catalog import (
    CatalogAggregatePut,
    CatalogShellCreate,
    DirectionWrite,
    ExamOptionWrite,
    ExamUnitWrite,
)
from app.schemas.admin_master_data import (
    CollegeCreate,
    ExamSubjectCreate,
    MajorCreate,
    SchoolCreate,
)
from app.services.admin_catalog import AdminCatalogService
from app.services.admin_master_data import (
    AdminMasterDataService,
    InvalidReferenceError,
    MasterDataWriteError,
)


def _catalog_key(catalog: CatalogImport) -> str:
    return (
        f"{catalog.school_code}/{catalog.college_code}/"
        f"{catalog.major_code}/{catalog.admission_year}/{catalog.study_mode}"
    )


def run_apply(data_path: Path, session: Session) -> ImportReport:
    report = ImportReport(mode="apply")
    document, manifest = load_document(data_path, report)
    if document is None or manifest is None or report.errors:
        return report
    if (
        manifest.source_type != "synthetic"
        or manifest.verification_status != "approved"
    ):
        report.errors.append(
            ImportErrorItem(
                path="/manifest",
                code="apply_source_not_allowed",
                message="--apply only accepts synthetic approved data",
            )
        )
        return report
    preflight(document, session, report)
    if report.errors:
        return report
    try:
        _write_stable_master(document, session, report)
        _write_catalogs(document, session, report)
    except MasterDataWriteError as exc:
        report.errors.append(
            ImportErrorItem(
                path="/",
                code=exc.code,
                message=exc.message,
            )
        )
        return report
    report.database_written = True
    return report


def _write_stable_master(
    document: ImportDocument,
    session: Session,
    report: ImportReport,
) -> None:
    planned = {(item.kind, item.key): item for item in report.planned}
    service = AdminMasterDataService(AdminSchoolRepository(session))
    repo = AdminSchoolRepository(session)
    for school in document.schools:
        item = planned[("school", school.school_code)]
        if item.action == "skip":
            continue
        service.create_school(
            SchoolCreate(school_code=school.school_code, name=school.name)
        )
    for college in document.colleges:
        key = f"{college.school_code}/{college.college_code}"
        item = planned[("college", key)]
        if item.action == "skip":
            continue
        parent = repo.get_school_by_code(college.school_code)
        if parent is None:
            raise RuntimeError(f"school missing after create: {college.school_code}")
        service.create_college(
            parent.id,
            CollegeCreate(college_code=college.college_code, name=college.name),
        )
    for major in document.majors:
        key = f"{major.school_code}/{major.major_code}"
        item = planned[("major", key)]
        if item.action == "skip":
            continue
        parent = repo.get_school_by_code(major.school_code)
        if parent is None:
            raise RuntimeError(f"school missing after create: {major.school_code}")
        service.create_major(
            parent.id,
            MajorCreate(
                major_code=major.major_code,
                name=major.name,
                degree_type=major.degree_type,
            ),
        )
    for subject in document.exam_subjects:
        if subject.scope == "national":
            item = planned[("exam_subject", f"national/{subject.subject_code}")]
            if item.action == "skip":
                continue
            service.create_national_exam_subject(
                ExamSubjectCreate(
                    subject_code=subject.subject_code,
                    name=subject.name,
                )
            )
            continue
        if not isinstance(subject, SchoolSubjectImport):
            continue
        item = planned[
            ("exam_subject", f"school/{subject.school_code}/{subject.subject_code}")
        ]
        if item.action == "skip":
            continue
        parent = repo.get_school_by_code(subject.school_code)
        if parent is None:
            raise RuntimeError(f"school missing after create: {subject.school_code}")
        service.create_school_exam_subject(
            parent.id,
            ExamSubjectCreate(
                subject_code=subject.subject_code,
                name=subject.name,
            ),
        )


def _write_catalogs(
    document: ImportDocument,
    session: Session,
    report: ImportReport,
) -> None:
    planned = {(item.kind, item.key): item for item in report.planned}
    masters = AdminSchoolRepository(session)
    service = AdminCatalogService(AdminCatalogRepository(session), masters)
    for catalog in document.catalogs:
        item = planned[("catalog", _catalog_key(catalog))]
        if item.action == "skip":
            continue
        school = masters.get_school_by_code(catalog.school_code)
        if school is None:
            raise InvalidReferenceError(f"school {catalog.school_code} not found")
        college = masters.get_college_by_school_and_code(
            school.id,
            catalog.college_code,
        )
        if college is None:
            raise InvalidReferenceError(
                f"college {catalog.school_code}/{catalog.college_code} not found"
            )
        major = masters.get_major_by_school_and_code(school.id, catalog.major_code)
        if major is None:
            raise InvalidReferenceError(
                f"major {catalog.school_code}/{catalog.major_code} not found"
            )
        shell = service.create_shell(
            CatalogShellCreate(
                school_id=school.id,
                college_id=college.id,
                major_id=major.id,
                admission_year=catalog.admission_year,
                study_mode=catalog.study_mode,
            )
        )
        service.replace_aggregate(
            shell.id,
            _catalog_put(catalog, school.id, college.id, major.id, masters),
        )


def _catalog_put(
    catalog: CatalogImport,
    school_id: int,
    college_id: int,
    major_id: int,
    masters: AdminSchoolRepository,
) -> CatalogAggregatePut:
    return CatalogAggregatePut(
        school_id=school_id,
        college_id=college_id,
        major_id=major_id,
        admission_year=catalog.admission_year,
        study_mode=catalog.study_mode,
        directions=[
            DirectionWrite(
                direction_code=item.direction_code,
                direction_name=item.direction_name,
            )
            for item in catalog.directions
        ],
        exam_units=[
            ExamUnitWrite(
                exam_unit=unit.exam_unit,
                options=[
                    ExamOptionWrite(
                        option_order=option.option_order,
                        exam_subject_id=_resolve_subject_id(masters, option),
                    )
                    for option in unit.options
                ],
            )
            for unit in catalog.exam_units
        ],
    )


def _resolve_subject_id(masters: AdminSchoolRepository, option: object) -> int:
    if isinstance(option, SchoolOptionImport):
        owner = masters.get_school_by_code(option.school_code)
        if owner is None:
            raise InvalidReferenceError(f"school {option.school_code} not found")
        subject = masters.get_school_subject_by_school_and_code(
            owner.id,
            option.subject_code,
        )
        if subject is None:
            raise InvalidReferenceError(
                f"school subject {option.school_code}/{option.subject_code} not found"
            )
        return subject.id
    subject = masters.get_national_subject_by_code(option.subject_code)
    if subject is None:
        raise InvalidReferenceError(
            f"national subject {option.subject_code} not found"
        )
    return subject.id
