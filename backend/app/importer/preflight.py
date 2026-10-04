from sqlalchemy.orm import Session

from app.importer.duplicates import check_document_duplicates
from app.importer.report import ImportErrorItem, ImportReport, PlannedItem
from app.importer.schemas import (
    CatalogImport,
    ImportDocument,
    SchoolOptionImport,
    SchoolSubjectImport,
)
from app.models import AdmissionCatalog, ExamSubject
from app.repositories.admin_catalog import AdminCatalogRepository
from app.repositories.admin_master_data import AdminSchoolRepository


def _error(report: ImportReport, path: str, code: str, message: str) -> None:
    report.errors.append(ImportErrorItem(path=path, code=code, message=message))


def _plan(
    report: ImportReport,
    kind: str,
    key: str,
    action: str,
    existing_inactive: bool = False,
) -> None:
    report.planned.append(
        PlannedItem(
            kind=kind,
            key=key,
            action=action,  # type: ignore[arg-type]
            existing_inactive=existing_inactive,
        )
    )


def _subject_identity(
    option: object,
) -> tuple[object, ...]:
    if isinstance(option, SchoolOptionImport):
        return ("school", option.school_code, option.subject_code)
    return ("national", option.subject_code)  # type: ignore[union-attr]


def _db_option_identity(
    subject: ExamSubject,
    schools: AdminSchoolRepository,
) -> tuple[object, ...]:
    if subject.school_id is None:
        return ("national", subject.subject_code)
    owner = schools.get_school(subject.school_id)
    school_code = owner.school_code if owner is not None else ""
    return ("school", school_code, subject.subject_code)


def _catalog_snapshot(
    catalog: AdmissionCatalog,
    catalogs: AdminCatalogRepository,
    schools: AdminSchoolRepository,
) -> tuple[tuple[object, ...], ...]:
    directions = tuple(
        sorted(
            (item.direction_code, item.direction_name)
            for item in catalogs.list_directions(catalog.id)
        )
    )
    units: dict[int, list[tuple[int, tuple[object, ...]]]] = {}
    for row in catalogs.list_exam_options(catalog.id):
        units.setdefault(row.link.exam_unit, []).append(
            (
                row.link.option_order,
                _db_option_identity(row.subject, schools),
            )
        )
    unit_snap = tuple(
        (exam_unit, tuple(sorted(options)))
        for exam_unit, options in sorted(units.items())
    )
    return directions, unit_snap


def _import_catalog_snapshot(
    catalog: CatalogImport,
) -> tuple[tuple[object, ...], ...]:
    directions = tuple(
        sorted(
            (item.direction_code, item.direction_name)
            for item in catalog.directions
        )
    )
    unit_snap = tuple(
        (
            unit.exam_unit,
            tuple(
                (option.option_order, _subject_identity(option))
                for option in sorted(unit.options, key=lambda item: item.option_order)
            ),
        )
        for unit in sorted(catalog.exam_units, key=lambda item: item.exam_unit)
    )
    return directions, unit_snap


def preflight(document: ImportDocument, session: Session, report: ImportReport) -> None:
    check_document_duplicates(document, report)
    schools_repo = AdminSchoolRepository(session)
    catalogs_repo = AdminCatalogRepository(session)

    for index, school in enumerate(document.schools):
        existing = schools_repo.get_school_by_code(school.school_code)
        path = f"/schools/{index}"
        if existing is None:
            _plan(report, "school", school.school_code, "create")
            continue
        if existing.name != school.name:
            _error(
                report,
                path,
                "conflict_existing",
                "existing school has different name",
            )
            continue
        _plan(
            report,
            "school",
            school.school_code,
            "skip",
            existing_inactive=not existing.is_active,
        )

    file_school_codes = {item.school_code for item in document.schools}

    def school_known(code: str) -> bool:
        if code in file_school_codes:
            return True
        return schools_repo.get_school_by_code(code) is not None

    for index, college in enumerate(document.colleges):
        path = f"/colleges/{index}"
        if not school_known(college.school_code):
            _error(
                report,
                f"{path}/school_code",
                "unknown_reference",
                "school_code is not in the document or database",
            )
            continue
        existing_school = schools_repo.get_school_by_code(college.school_code)
        existing = None
        if existing_school is not None:
            existing = schools_repo.get_college_by_school_and_code(
                existing_school.id,
                college.college_code,
            )
        key = f"{college.school_code}/{college.college_code}"
        if existing is None:
            if existing_school is not None and not existing_school.is_active:
                _error(
                    report,
                    path,
                    "parent_inactive",
                    "school is inactive; college create is rejected",
                )
                continue
            _plan(report, "college", key, "create")
            continue
        if existing.name != college.name:
            _error(
                report,
                path,
                "conflict_existing",
                "existing college has different name",
            )
            continue
        _plan(
            report,
            "college",
            key,
            "skip",
            existing_inactive=not existing.is_active,
        )

    for index, major in enumerate(document.majors):
        path = f"/majors/{index}"
        if not school_known(major.school_code):
            _error(
                report,
                f"{path}/school_code",
                "unknown_reference",
                "school_code is not in the document or database",
            )
            continue
        existing_school = schools_repo.get_school_by_code(major.school_code)
        existing = None
        if existing_school is not None:
            existing = schools_repo.get_major_by_school_and_code(
                existing_school.id,
                major.major_code,
            )
        key = f"{major.school_code}/{major.major_code}"
        if existing is None:
            if existing_school is not None and not existing_school.is_active:
                _error(
                    report,
                    path,
                    "parent_inactive",
                    "school is inactive; major create is rejected",
                )
                continue
            _plan(report, "major", key, "create")
            continue
        if existing.name != major.name or existing.degree_type != major.degree_type:
            _error(
                report,
                path,
                "conflict_existing",
                "existing major has different fields",
            )
            continue
        _plan(
            report,
            "major",
            key,
            "skip",
            existing_inactive=not existing.is_active,
        )

    file_national = {
        item.subject_code
        for item in document.exam_subjects
        if item.scope == "national"
    }
    file_school_subjects = {
        (item.school_code, item.subject_code)
        for item in document.exam_subjects
        if isinstance(item, SchoolSubjectImport)
    }

    for index, subject in enumerate(document.exam_subjects):
        path = f"/exam_subjects/{index}"
        if subject.scope == "national":
            existing = schools_repo.get_national_subject_by_code(subject.subject_code)
            key = f"national/{subject.subject_code}"
            if existing is None:
                _plan(report, "exam_subject", key, "create")
                continue
            if existing.name != subject.name:
                _error(
                    report,
                    path,
                    "conflict_existing",
                    "existing national subject has different name",
                )
                continue
            _plan(
                report,
                "exam_subject",
                key,
                "skip",
                existing_inactive=not existing.is_active,
            )
            continue
        if not school_known(subject.school_code):
            _error(
                report,
                f"{path}/school_code",
                "unknown_reference",
                "school_code is not in the document or database",
            )
            continue
        existing_school = schools_repo.get_school_by_code(subject.school_code)
        existing = None
        if existing_school is not None:
            existing = schools_repo.get_school_subject_by_school_and_code(
                existing_school.id,
                subject.subject_code,
            )
        key = f"school/{subject.school_code}/{subject.subject_code}"
        if existing is None:
            if existing_school is not None and not existing_school.is_active:
                _error(
                    report,
                    path,
                    "parent_inactive",
                    "school is inactive; school subject create is rejected",
                )
                continue
            _plan(report, "exam_subject", key, "create")
            continue
        if existing.name != subject.name:
            _error(
                report,
                path,
                "conflict_existing",
                "existing school subject has different name",
            )
            continue
        _plan(
            report,
            "exam_subject",
            key,
            "skip",
            existing_inactive=not existing.is_active,
        )

    def subject_known(option: object, catalog_school: str, path: str) -> bool:
        if isinstance(option, SchoolOptionImport):
            if option.school_code != catalog_school:
                _error(
                    report,
                    path,
                    "reference_scope_mismatch",
                    "school subject does not belong to catalog school",
                )
                return False
            if (option.school_code, option.subject_code) in file_school_subjects:
                return True
            owner = schools_repo.get_school_by_code(option.school_code)
            if owner is None:
                _error(
                    report,
                    path,
                    "unknown_reference",
                    "school subject school_code is unknown",
                )
                return False
            found = schools_repo.get_school_subject_by_school_and_code(
                owner.id,
                option.subject_code,
            )
            if found is None:
                _error(
                    report,
                    path,
                    "unknown_reference",
                    "school subject is not in the document or database",
                )
                return False
            return True
        code = option.subject_code  # type: ignore[union-attr]
        if code in file_national:
            return True
        found = schools_repo.get_national_subject_by_code(code)
        if found is None:
            _error(
                report,
                path,
                "unknown_reference",
                "national subject is not in the document or database",
            )
            return False
        return True

    for index, catalog in enumerate(document.catalogs):
        path = f"/catalogs/{index}"
        if not school_known(catalog.school_code):
            _error(
                report,
                f"{path}/school_code",
                "unknown_reference",
                "school_code is not in the document or database",
            )
            continue
        college_in_file = any(
            item.school_code == catalog.school_code
            and item.college_code == catalog.college_code
            for item in document.colleges
        )
        major_in_file = any(
            item.school_code == catalog.school_code
            and item.major_code == catalog.major_code
            for item in document.majors
        )
        school_row = schools_repo.get_school_by_code(catalog.school_code)
        college_row = None
        major_row = None
        if school_row is not None:
            college_row = schools_repo.get_college_by_school_and_code(
                school_row.id,
                catalog.college_code,
            )
            major_row = schools_repo.get_major_by_school_and_code(
                school_row.id,
                catalog.major_code,
            )
        if not college_in_file and college_row is None:
            _error(
                report,
                f"{path}/college_code",
                "unknown_reference",
                "college is not in the document or database",
            )
            continue
        if not major_in_file and major_row is None:
            _error(
                report,
                f"{path}/major_code",
                "unknown_reference",
                "major is not in the document or database",
            )
            continue
        if college_in_file:
            file_college = next(
                item
                for item in document.colleges
                if item.school_code == catalog.school_code
                and item.college_code == catalog.college_code
            )
            if file_college.school_code != catalog.school_code:
                _error(
                    report,
                    path,
                    "reference_scope_mismatch",
                    "college does not belong to catalog school",
                )
                continue
        if (
            college_row is not None
            and school_row is not None
            and college_row.school_id != school_row.id
        ):
            _error(
                report,
                path,
                "reference_scope_mismatch",
                "college does not belong to catalog school",
            )
            continue
        options_ok = True
        for unit_index, unit in enumerate(catalog.exam_units):
            for opt_index, option in enumerate(unit.options):
                opt_path = (
                    f"{path}/exam_units/{unit_index}/options/{opt_index}"
                )
                if not subject_known(option, catalog.school_code, opt_path):
                    options_ok = False
        if not options_ok:
            continue
        key = (
            f"{catalog.school_code}/{catalog.college_code}/"
            f"{catalog.major_code}/{catalog.admission_year}/{catalog.study_mode}"
        )
        existing_catalog = None
        if school_row is not None and college_row is not None and major_row is not None:
            existing_catalog = catalogs_repo.get_catalog_by_offering(
                school_id=school_row.id,
                college_id=college_row.id,
                major_id=major_row.id,
                admission_year=catalog.admission_year,
                study_mode=catalog.study_mode,
            )
        if existing_catalog is None:
            inactive_ref = None
            if school_row is not None and not school_row.is_active:
                inactive_ref = "school"
            elif college_row is not None and not college_row.is_active:
                inactive_ref = "college"
            elif major_row is not None and not major_row.is_active:
                inactive_ref = "major"
            if inactive_ref is not None:
                _error(
                    report,
                    path,
                    "inactive_reference",
                    f"{inactive_ref} is inactive; catalog shell create is rejected",
                )
                continue
            _plan(report, "catalog", key, "create")
            continue
        imported = _import_catalog_snapshot(catalog)
        current = _catalog_snapshot(existing_catalog, catalogs_repo, schools_repo)
        if imported != current:
            _error(
                report,
                path,
                "conflict_existing",
                "existing catalog aggregate differs; import will not overwrite",
            )
            continue
        _plan(
            report,
            "catalog",
            key,
            "skip",
            existing_inactive=not existing_catalog.is_active,
        )
