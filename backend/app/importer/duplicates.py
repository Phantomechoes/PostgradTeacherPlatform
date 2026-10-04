from app.importer.report import ImportErrorItem, ImportReport
from app.importer.schemas import ImportDocument, SchoolOptionImport


def _dup(report: ImportReport, path: str, message: str) -> None:
    report.errors.append(
        ImportErrorItem(path=path, code="duplicate_in_document", message=message)
    )


def check_document_duplicates(document: ImportDocument, report: ImportReport) -> None:
    seen_schools: dict[str, int] = {}
    for index, school in enumerate(document.schools):
        if school.school_code in seen_schools:
            _dup(
                report,
                f"/schools/{index}/school_code",
                f"duplicate school_code {school.school_code}",
            )
        seen_schools[school.school_code] = index

    seen_colleges: dict[tuple[str, str], int] = {}
    for index, college in enumerate(document.colleges):
        key = (college.school_code, college.college_code)
        if key in seen_colleges:
            _dup(
                report,
                f"/colleges/{index}/college_code",
                "duplicate college_code in school",
            )
        seen_colleges[key] = index

    seen_majors: dict[tuple[str, str], int] = {}
    for index, major in enumerate(document.majors):
        key = (major.school_code, major.major_code)
        if key in seen_majors:
            _dup(
                report,
                f"/majors/{index}/major_code",
                "duplicate major_code in school",
            )
        seen_majors[key] = index

    seen_national: dict[str, int] = {}
    seen_school_subjects: dict[tuple[str, str], int] = {}
    for index, subject in enumerate(document.exam_subjects):
        if subject.scope == "national":
            if subject.subject_code in seen_national:
                _dup(
                    report,
                    f"/exam_subjects/{index}/subject_code",
                    "duplicate national subject_code",
                )
            seen_national[subject.subject_code] = index
        else:
            key = (subject.school_code, subject.subject_code)
            if key in seen_school_subjects:
                _dup(
                    report,
                    f"/exam_subjects/{index}/subject_code",
                    "duplicate school subject_code",
                )
            seen_school_subjects[key] = index

    seen_catalogs: dict[tuple[str, str, str, int, str], int] = {}
    for catalog_index, catalog in enumerate(document.catalogs):
        offering = (
            catalog.school_code,
            catalog.college_code,
            catalog.major_code,
            catalog.admission_year,
            catalog.study_mode,
        )
        if offering in seen_catalogs:
            _dup(
                report,
                f"/catalogs/{catalog_index}",
                "duplicate catalog offering",
            )
        seen_catalogs[offering] = catalog_index
        seen_dirs: dict[str, int] = {}
        for dir_index, direction in enumerate(catalog.directions):
            if direction.direction_code in seen_dirs:
                _dup(
                    report,
                    f"/catalogs/{catalog_index}/directions/{dir_index}/direction_code",
                    "duplicate direction_code",
                )
            seen_dirs[direction.direction_code] = dir_index
        seen_units: dict[int, int] = {}
        for unit_index, unit in enumerate(catalog.exam_units):
            if unit.exam_unit in seen_units:
                _dup(
                    report,
                    f"/catalogs/{catalog_index}/exam_units/{unit_index}/exam_unit",
                    "duplicate exam_unit",
                )
            seen_units[unit.exam_unit] = unit_index
            seen_orders: dict[int, int] = {}
            seen_subjects: dict[tuple[object, ...], int] = {}
            for opt_index, option in enumerate(unit.options):
                if option.option_order in seen_orders:
                    _dup(
                        report,
                        f"/catalogs/{catalog_index}/exam_units/{unit_index}/options/{opt_index}/option_order",
                        "duplicate option_order",
                    )
                seen_orders[option.option_order] = opt_index
                if isinstance(option, SchoolOptionImport):
                    identity = (
                        "school",
                        option.school_code,
                        option.subject_code,
                    )
                else:
                    identity = ("national", option.subject_code)
                if identity in seen_subjects:
                    _dup(
                        report,
                        f"/catalogs/{catalog_index}/exam_units/{unit_index}/options/{opt_index}",
                        "duplicate subject in exam_unit",
                    )
                seen_subjects[identity] = opt_index
