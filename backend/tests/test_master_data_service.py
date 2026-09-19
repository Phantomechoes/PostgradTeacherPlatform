from types import SimpleNamespace

import pytest

from app.repositories.master_data import CatalogExamOptionRow, CatalogRow
from app.services.master_data import MasterDataNotFoundError, MasterDataReadService


def _school(**overrides):
    values = {
        "id": 1,
        "school_code": "10001",
        "name": "北京交通大学",
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _college(**overrides):
    values = {
        "id": 2,
        "school_id": 1,
        "college_code": "AI",
        "name": "自动化与智能学院",
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _major(**overrides):
    values = {
        "id": 3,
        "school_id": 1,
        "major_code": "140500",
        "name": "智能科学与技术",
        "degree_type": "academic",
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _catalog(**overrides):
    values = {
        "id": 10,
        "admission_year": 2026,
        "study_mode": "full_time",
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _catalog_row() -> CatalogRow:
    return CatalogRow(
        catalog=_catalog(),
        school=_school(),
        college=_college(),
        major=_major(),
    )


def _option_row(
    *,
    exam_unit: int,
    option_order: int,
    link_id: int,
    subject_code: str,
    school_id: int | None = None,
    is_active: bool = True,
) -> CatalogExamOptionRow:
    return CatalogExamOptionRow(
        link=SimpleNamespace(
            id=link_id,
            exam_unit=exam_unit,
            option_order=option_order,
        ),
        subject=SimpleNamespace(
            id=link_id,
            subject_code=subject_code,
            name=subject_code,
            school_id=school_id,
            is_active=is_active,
        ),
    )


_DEFAULT_SCHOOL = _school()


class FakeSchoolRepository:
    def __init__(
        self,
        *,
        school=_DEFAULT_SCHOOL,
        schools: list | None = None,
        total: int = 1,
        colleges: list | None = None,
        majors: list | None = None,
        years: list[int] | None = None,
    ) -> None:
        self.school = school
        self.schools = schools if schools is not None else [school] if school else []
        self.total = total
        self.colleges = colleges if colleges is not None else []
        self.majors = majors if majors is not None else []
        self.years = years if years is not None else []
        self.list_schools_calls: list[dict] = []
        self.get_active_by_id_calls: list[int] = []
        self.list_colleges_calls: list[int] = []
        self.list_majors_calls: list[int] = []
        self.list_admission_years_calls: list[int] = []

    def get_active_by_id(self, school_id: int):
        self.get_active_by_id_calls.append(school_id)
        if self.school is None or self.school.id != school_id:
            return None
        return self.school

    def list_schools(self, *, q, offset, limit):
        self.list_schools_calls.append({"q": q, "offset": offset, "limit": limit})
        return self.schools, self.total

    def list_colleges(self, school_id: int):
        self.list_colleges_calls.append(school_id)
        return self.colleges

    def list_majors(self, school_id: int):
        self.list_majors_calls.append(school_id)
        return self.majors

    def list_admission_years(self, school_id: int):
        self.list_admission_years_calls.append(school_id)
        return self.years


class FakeCatalogRepository:
    def __init__(
        self,
        *,
        row: CatalogRow | None = None,
        rows: list[CatalogRow] | None = None,
        total: int = 0,
        directions: list | None = None,
        options: list[CatalogExamOptionRow] | None = None,
    ) -> None:
        self.row = row
        self.rows = rows if rows is not None else []
        self.total = total
        self.directions = directions if directions is not None else []
        self.options = options if options is not None else []
        self.list_catalogs_calls: list[dict] = []
        self.get_catalog_calls: list[int] = []
        self.list_directions_calls: list[int] = []
        self.list_exam_options_calls: list[int] = []

    def list_catalogs(self, **kwargs):
        self.list_catalogs_calls.append(kwargs)
        return self.rows, self.total

    def get_catalog(self, catalog_id: int):
        self.get_catalog_calls.append(catalog_id)
        if self.row is None or self.row.catalog.id != catalog_id:
            return None
        return self.row

    def list_directions(self, catalog_id: int):
        self.list_directions_calls.append(catalog_id)
        return self.directions

    def list_exam_options(self, catalog_id: int):
        self.list_exam_options_calls.append(catalog_id)
        return self.options


def _service(schools=None, catalogs=None) -> MasterDataReadService:
    return MasterDataReadService(
        schools if schools is not None else FakeSchoolRepository(),
        catalogs if catalogs is not None else FakeCatalogRepository(),
    )


def test_list_schools_strips_q() -> None:
    schools = FakeSchoolRepository()
    _service(schools=schools).list_schools(q="  交大  ", page=1, page_size=20)
    assert schools.list_schools_calls[0]["q"] == "交大"


def test_list_schools_blank_q_becomes_none() -> None:
    schools = FakeSchoolRepository()
    _service(schools=schools).list_schools(q="   ", page=1, page_size=20)
    assert schools.list_schools_calls[0]["q"] is None


def test_list_schools_none_q_stays_none() -> None:
    schools = FakeSchoolRepository()
    _service(schools=schools).list_schools(q=None, page=1, page_size=20)
    assert schools.list_schools_calls[0]["q"] is None


def test_list_schools_converts_page_to_offset_and_limit() -> None:
    schools = FakeSchoolRepository()
    page = _service(schools=schools).list_schools(q=None, page=3, page_size=10)
    assert schools.list_schools_calls[0] == {"q": None, "offset": 20, "limit": 10}
    assert page.page == 3
    assert page.page_size == 10
    assert page.total == 1
    assert page.items[0].name == "北京交通大学"


def test_get_school_none_raises_not_found() -> None:
    service = _service(schools=FakeSchoolRepository(school=None, schools=[], total=0))
    with pytest.raises(MasterDataNotFoundError) as exc_info:
        service.get_school(99)
    assert exc_info.value.resource == "school"
    assert exc_info.value.resource_id == 99


def test_get_school_maps_summary() -> None:
    result = _service().get_school(1)
    assert result.id == 1
    assert result.school_code == "10001"
    assert not hasattr(result, "is_active")


@pytest.mark.parametrize(
    ("method_name", "call_attr"),
    [
        ("list_colleges", "list_colleges_calls"),
        ("list_majors", "list_majors_calls"),
        ("list_admission_years", "list_admission_years_calls"),
    ],
)
def test_school_child_endpoints_require_active_school(
    method_name: str,
    call_attr: str,
) -> None:
    schools = FakeSchoolRepository(school=None)
    service = _service(schools=schools)
    with pytest.raises(MasterDataNotFoundError) as exc_info:
        getattr(service, method_name)(8)
    assert exc_info.value.resource == "school"
    assert exc_info.value.resource_id == 8
    assert getattr(schools, call_attr) == []


def test_list_colleges_after_active_school() -> None:
    schools = FakeSchoolRepository(colleges=[_college(college_code=None)])
    result = _service(schools=schools).list_colleges(1)
    assert schools.get_active_by_id_calls == [1]
    assert schools.list_colleges_calls == [1]
    assert result[0].college_code is None


def test_list_admission_years_wraps_items() -> None:
    schools = FakeSchoolRepository(years=[2027, 2026])
    result = _service(schools=schools).list_admission_years(1)
    assert result.items == [2027, 2026]


def test_list_catalogs_empty_is_empty_page_not_not_found() -> None:
    schools = FakeSchoolRepository(school=None)
    catalogs = FakeCatalogRepository(rows=[], total=0)
    result = _service(schools=schools, catalogs=catalogs).list_catalogs(
        school_id=999,
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode=None,
        page=1,
        page_size=20,
    )
    assert schools.get_active_by_id_calls == []
    assert result.items == []
    assert result.total == 0
    assert result.page == 1
    assert result.page_size == 20


def test_list_catalogs_converts_page_to_offset() -> None:
    catalogs = FakeCatalogRepository(rows=[], total=0)
    _service(catalogs=catalogs).list_catalogs(
        school_id=1,
        admission_year=2026,
        college_id=2,
        major_id=3,
        study_mode="full_time",
        page=2,
        page_size=20,
    )
    assert catalogs.list_catalogs_calls[0]["offset"] == 20
    assert catalogs.list_catalogs_calls[0]["limit"] == 20
    assert catalogs.list_catalogs_calls[0]["school_id"] == 1


def test_list_catalogs_maps_summary_without_internal_fields() -> None:
    catalogs = FakeCatalogRepository(rows=[_catalog_row()], total=1)
    page = _service(catalogs=catalogs).list_catalogs(
        school_id=1,
        admission_year=None,
        college_id=None,
        major_id=None,
        study_mode=None,
        page=1,
        page_size=20,
    )
    item = page.items[0]
    dumped = item.model_dump()
    assert "is_active" not in dumped
    assert "created_at" not in dumped
    assert dumped["school"]["name"] == "北京交通大学"
    assert dumped["college"]["name"] == "自动化与智能学院"
    assert dumped["major"]["major_code"] == "140500"


def test_get_catalog_detail_none_raises_not_found() -> None:
    catalogs = FakeCatalogRepository(row=None)
    service = _service(catalogs=catalogs)
    with pytest.raises(MasterDataNotFoundError) as exc_info:
        service.get_catalog_detail(44)
    assert exc_info.value.resource == "admission_catalog"
    assert exc_info.value.resource_id == 44
    assert catalogs.list_directions_calls == []
    assert catalogs.list_exam_options_calls == []


def test_get_catalog_detail_uses_three_queries_and_empty_directions() -> None:
    catalogs = FakeCatalogRepository(row=_catalog_row(), directions=[], options=[])
    detail = _service(catalogs=catalogs).get_catalog_detail(10)
    assert catalogs.get_catalog_calls == [10]
    assert catalogs.list_directions_calls == [10]
    assert catalogs.list_exam_options_calls == [10]
    assert detail.directions == []
    assert detail.exam_units == []


def test_exam_units_group_two_units_and_or_options() -> None:
    catalogs = FakeCatalogRepository(
        row=_catalog_row(),
        options=[
            _option_row(
                exam_unit=1, option_order=1, link_id=1, subject_code="101"
            ),
            _option_row(
                exam_unit=2, option_order=1, link_id=2, subject_code="201"
            ),
            _option_row(
                exam_unit=2, option_order=2, link_id=3, subject_code="204"
            ),
        ],
    )
    detail = _service(catalogs=catalogs).get_catalog_detail(10)
    assert [unit.exam_unit for unit in detail.exam_units] == [1, 2]
    assert [opt.subject.subject_code for opt in detail.exam_units[0].options] == [
        "101"
    ]
    assert [opt.subject.subject_code for opt in detail.exam_units[1].options] == [
        "201",
        "204",
    ]
    assert [opt.option_order for opt in detail.exam_units[1].options] == [1, 2]


def test_service_does_not_refilter_inactive_exam_subject() -> None:
    catalogs = FakeCatalogRepository(
        row=_catalog_row(),
        options=[
            _option_row(
                exam_unit=1,
                option_order=1,
                link_id=9,
                subject_code="895",
                school_id=1,
                is_active=False,
            )
        ],
    )
    detail = _service(catalogs=catalogs).get_catalog_detail(10)
    assert len(detail.exam_units) == 1
    assert detail.exam_units[0].options[0].subject.subject_code == "895"


def test_not_found_error_is_not_http_exception() -> None:
    import fastapi

    assert not issubclass(MasterDataNotFoundError, fastapi.HTTPException)
