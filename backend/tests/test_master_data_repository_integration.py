from sqlalchemy.orm import Session

from app.repositories.master_data import AdmissionCatalogRepository, SchoolRepository
from tests.conftest import (
    CATALOG_2026_FT_ID,
    CATALOG_2026_PT_ID,
    CATALOG_2027_ID,
    CATALOG_INACTIVE_COLLEGE_ID,
    CATALOG_INACTIVE_ID,
    CATALOG_INACTIVE_MAJOR_ID,
    CATALOG_SCHOOL_C_ID,
    COLLEGE_A_ID,
    COLLEGE_B_ID,
    COLLEGE_C_ID,
    COLLEGE_NULL_ID,
    DIRECTION_01_ID,
    DIRECTION_02_ID,
    LINK_UNIT1_ID,
    LINK_UNIT2_OPT1_ID,
    LINK_UNIT2_OPT2_ID,
    MAJOR_A2_ID,
    MAJOR_A_ID,
    PREFIX,
    SCHOOL_A_ID,
    SCHOOL_B_INACTIVE_ID,
    SCHOOL_C_ID,
    SCHOOL_D_ID,
    SCHOOL_E_ID,
    SUBJECT_ALT_ID,
    SUBJECT_INACTIVE_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)


def _schools(session: Session) -> SchoolRepository:
    return SchoolRepository(session)


def _catalogs(session: Session) -> AdmissionCatalogRepository:
    return AdmissionCatalogRepository(session)


def test_get_active_by_id_returns_active(seeded_session: Session) -> None:
    school = _schools(seeded_session).get_active_by_id(SCHOOL_A_ID)
    assert school is not None
    assert school.id == SCHOOL_A_ID
    assert school.school_code == f"{PREFIX}_A"


def test_get_active_by_id_hides_inactive(seeded_session: Session) -> None:
    assert _schools(seeded_session).get_active_by_id(SCHOOL_B_INACTIVE_ID) is None


def test_get_active_by_id_missing(seeded_session: Session) -> None:
    assert _schools(seeded_session).get_active_by_id(9_199_999) is None


def test_list_schools_excludes_inactive(seeded_session: Session) -> None:
    items, total = _schools(seeded_session).list_schools(
        q=PREFIX, offset=0, limit=20
    )
    codes = [school.school_code for school in items]
    assert f"{PREFIX}_B" not in codes
    assert codes == [
        f"{PREFIX}_A",
        f"{PREFIX}_C",
        f"{PREFIX}_D",
        f"{PREFIX}_E",
    ]
    assert total == 4


def test_list_schools_ilike_code_and_name_case_insensitive(
    seeded_session: Session,
) -> None:
    by_code, code_total = _schools(seeded_session).list_schools(
        q=f"{PREFIX}_a".lower(),
        offset=0,
        limit=20,
    )
    assert code_total == 1
    assert by_code[0].id == SCHOOL_A_ID

    by_name, name_total = _schools(seeded_session).list_schools(
        q="ALPHAUNIVERSITY",
        offset=0,
        limit=20,
    )
    assert name_total == 1
    assert by_name[0].id == SCHOOL_A_ID


def test_list_schools_pagination_total_independent_of_page(
    seeded_session: Session,
) -> None:
    page1, total1 = _schools(seeded_session).list_schools(
        q=PREFIX, offset=0, limit=2
    )
    page2, total2 = _schools(seeded_session).list_schools(
        q=PREFIX, offset=2, limit=2
    )
    assert total1 == 4
    assert total2 == 4
    assert len(page1) == 2
    assert len(page2) == 2
    assert [school.id for school in page1] == [SCHOOL_A_ID, SCHOOL_C_ID]
    assert [school.id for school in page2] == [SCHOOL_D_ID, SCHOOL_E_ID]


def test_list_colleges_active_only_nulls_last(seeded_session: Session) -> None:
    colleges = _schools(seeded_session).list_colleges(SCHOOL_A_ID)
    assert [college.id for college in colleges] == [
        COLLEGE_A_ID,
        COLLEGE_B_ID,
        COLLEGE_NULL_ID,
    ]
    assert colleges[0].college_code == "A_COL"
    assert colleges[1].college_code == "B_COL"
    assert colleges[2].college_code is None
    assert all(college.is_active for college in colleges)


def test_list_majors_active_only_stable_sort(seeded_session: Session) -> None:
    majors = _schools(seeded_session).list_majors(SCHOOL_A_ID)
    assert [major.id for major in majors] == [MAJOR_A_ID, MAJOR_A2_ID]
    assert [major.major_code for major in majors] == [
        f"{PREFIX}_140500",
        f"{PREFIX}_140501",
    ]


def test_list_admission_years_distinct_desc_and_visible_only(
    seeded_session: Session,
) -> None:
    years = _schools(seeded_session).list_admission_years(SCHOOL_A_ID)
    assert years == [2027, 2026]


def test_list_admission_years_empty_when_no_visible_catalog(
    seeded_session: Session,
) -> None:
    assert _schools(seeded_session).list_admission_years(SCHOOL_D_ID) == []


def test_list_catalogs_visible_only_sorted(seeded_session: Session) -> None:
    rows, total = _catalogs(seeded_session).list_catalogs(
        school_id=SCHOOL_A_ID,
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode=None,
        offset=0,
        limit=20,
    )
    assert total == 3
    assert [row.catalog.id for row in rows] == [
        CATALOG_2027_ID,
        CATALOG_2026_FT_ID,
        CATALOG_2026_PT_ID,
    ]
    hidden = {
        CATALOG_INACTIVE_ID,
        CATALOG_INACTIVE_COLLEGE_ID,
        CATALOG_INACTIVE_MAJOR_ID,
        CATALOG_SCHOOL_C_ID,
    }
    assert hidden.isdisjoint({row.catalog.id for row in rows})


def test_list_catalogs_year_filter(seeded_session: Session) -> None:
    rows, total = _catalogs(seeded_session).list_catalogs(
        school_id=SCHOOL_A_ID,
        admission_year=2026,
        college_id=None,
        major_id=None,
        study_mode=None,
        offset=0,
        limit=20,
    )
    assert total == 2
    assert {row.catalog.id for row in rows} == {
        CATALOG_2026_FT_ID,
        CATALOG_2026_PT_ID,
    }


def test_list_catalogs_college_major_study_mode_filters(
    seeded_session: Session,
) -> None:
    by_college, college_total = _catalogs(seeded_session).list_catalogs(
        school_id=SCHOOL_A_ID,
        admission_year=None,
        college_id=COLLEGE_A_ID,
        major_id=None,
        study_mode=None,
        offset=0,
        limit=20,
    )
    assert college_total == 3
    assert len(by_college) == 3

    by_major, major_total = _catalogs(seeded_session).list_catalogs(
        school_id=SCHOOL_A_ID,
        admission_year=None,
        college_id=None,
        major_id=MAJOR_A_ID,
        study_mode=None,
        offset=0,
        limit=20,
    )
    assert major_total == 3
    assert len(by_major) == 3

    by_mode, mode_total = _catalogs(seeded_session).list_catalogs(
        school_id=SCHOOL_A_ID,
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode="part_time",
        offset=0,
        limit=20,
    )
    assert mode_total == 1
    assert by_mode[0].catalog.id == CATALOG_2026_PT_ID


def test_list_catalogs_school_mismatch_empty(seeded_session: Session) -> None:
    rows, total = _catalogs(seeded_session).list_catalogs(
        school_id=SCHOOL_A_ID,
        admission_year=None,
        college_id=COLLEGE_C_ID,
        major_id=None,
        study_mode=None,
        offset=0,
        limit=20,
    )
    assert rows == []
    assert total == 0


def test_list_catalogs_unknown_school_empty_page(seeded_session: Session) -> None:
    rows, total = _catalogs(seeded_session).list_catalogs(
        school_id=9_199_999,
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode=None,
        offset=0,
        limit=20,
    )
    assert rows == []
    assert total == 0


def test_list_catalogs_total_independent_of_pagination(
    seeded_session: Session,
) -> None:
    page, total = _catalogs(seeded_session).list_catalogs(
        school_id=SCHOOL_A_ID,
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode=None,
        offset=0,
        limit=1,
    )
    assert len(page) == 1
    assert total == 3
    assert page[0].catalog.id == CATALOG_2027_ID


def test_get_catalog_visible_row(seeded_session: Session) -> None:
    row = _catalogs(seeded_session).get_catalog(CATALOG_2027_ID)
    assert row is not None
    assert row.catalog.id == CATALOG_2027_ID
    assert row.school.id == SCHOOL_A_ID
    assert row.college.id == COLLEGE_A_ID
    assert row.major.id == MAJOR_A_ID


def test_get_catalog_inactive_or_parent_inactive_is_none(
    seeded_session: Session,
) -> None:
    repo = _catalogs(seeded_session)
    assert repo.get_catalog(CATALOG_INACTIVE_ID) is None
    assert repo.get_catalog(CATALOG_INACTIVE_COLLEGE_ID) is None
    assert repo.get_catalog(CATALOG_INACTIVE_MAJOR_ID) is None
    assert repo.get_catalog(9_199_999) is None


def test_list_directions_sorted(seeded_session: Session) -> None:
    directions = _catalogs(seeded_session).list_directions(CATALOG_2027_ID)
    assert [item.direction_code for item in directions] == ["01", "02"]
    assert [item.id for item in directions] == [DIRECTION_01_ID, DIRECTION_02_ID]


def test_list_directions_empty(seeded_session: Session) -> None:
    assert _catalogs(seeded_session).list_directions(CATALOG_2026_FT_ID) == []


def test_list_exam_options_sort_and_skip_inactive_subject(
    seeded_session: Session,
) -> None:
    options = _catalogs(seeded_session).list_exam_options(CATALOG_2027_ID)
    assert [row.link.id for row in options] == [
        LINK_UNIT1_ID,
        LINK_UNIT2_OPT1_ID,
        LINK_UNIT2_OPT2_ID,
    ]
    assert [row.link.exam_unit for row in options] == [1, 2, 2]
    assert [row.link.option_order for row in options] == [1, 1, 2]
    subject_ids = {row.subject.id for row in options}
    assert SUBJECT_NATIONAL_ID in subject_ids
    assert SUBJECT_SCHOOL_ID in subject_ids
    assert SUBJECT_ALT_ID in subject_ids
    assert SUBJECT_INACTIVE_ID not in subject_ids
