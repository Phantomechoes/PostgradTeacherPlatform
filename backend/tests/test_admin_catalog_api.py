import inspect
from collections.abc import Generator
from typing import get_args

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.admin_catalog import (
    get_admin_catalog_read_service,
    get_admin_catalog_write_service,
)
from app.core.database import get_db, get_write_db
from app.main import app
from app.repositories.admin_catalog import AdminCatalogRepository
from tests.conftest import (
    CATALOG_2026_FT_ID,
    CATALOG_2027_ID,
    CATALOG_INACTIVE_ID,
    CATALOG_SCHOOL_C_ID,
    COLLEGE_A_ID,
    COLLEGE_C_ID,
    COLLEGE_INACTIVE_ID,
    MAJOR_A_ID,
    MAJOR_C_ID,
    MAJOR_INACTIVE_ID,
    SCHOOL_A_ID,
    SCHOOL_B_INACTIVE_ID,
    SCHOOL_C_ID,
    SUBJECT_ALT_ID,
    SUBJECT_INACTIVE_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

ADMIN = "/api/v1/admin/admission-catalogs"
PUBLIC = "/api/v1/admission-catalogs"
MASTER = "/api/v1/admin"
SHELL_YEAR = 2035


def _code(response) -> str:
    return response.json()["detail"]["code"]


def _assert_business_error(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert body["detail"]["code"] == code
    assert isinstance(body["detail"]["message"], str)
    text = response.text.lower()
    assert "psycopg" not in text
    assert "sqlalchemy" not in text
    assert "duplicate key" not in text


def _shell(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "school_id": SCHOOL_A_ID,
        "college_id": COLLEGE_A_ID,
        "major_id": MAJOR_A_ID,
        "admission_year": SHELL_YEAR,
        "study_mode": "full_time",
    }
    body.update(overrides)
    return body


def _put(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "school_id": SCHOOL_A_ID,
        "college_id": COLLEGE_A_ID,
        "major_id": MAJOR_A_ID,
        "admission_year": 2026,
        "study_mode": "full_time",
        "directions": [],
        "exam_units": [],
    }
    body.update(overrides)
    return body


def _active_units() -> list[dict[str, object]]:
    return [
        {
            "exam_unit": 1,
            "options": [
                {"option_order": 1, "exam_subject_id": SUBJECT_NATIONAL_ID},
            ],
        },
        {
            "exam_unit": 2,
            "options": [
                {"option_order": 1, "exam_subject_id": SUBJECT_SCHOOL_ID},
                {"option_order": 3, "exam_subject_id": SUBJECT_ALT_ID},
            ],
        },
    ]


def _subject_ids(detail: dict) -> set[int]:
    return {
        option["subject"]["id"]
        for unit in detail["exam_units"]
        for option in unit["options"]
    }


def _public_ids(client: TestClient, school_id: int) -> set[int]:
    response = client.get(PUBLIC, params={"school_id": school_id, "page_size": 100})
    assert response.status_code == 200
    return {item["id"] for item in response.json()["items"]}


def _snapshot(session: Session, catalog_id: int) -> dict[str, object]:
    repo = AdminCatalogRepository(session)
    row = repo.get_catalog_row(catalog_id)
    assert row is not None
    catalog = row.catalog
    return {
        "school_id": catalog.school_id,
        "college_id": catalog.college_id,
        "major_id": catalog.major_id,
        "admission_year": catalog.admission_year,
        "study_mode": catalog.study_mode,
        "is_active": catalog.is_active,
        "directions": [
            (item.direction_code, item.direction_name)
            for item in repo.list_directions(catalog_id)
        ],
        "options": [
            (item.link.exam_unit, item.link.option_order, item.subject.id)
            for item in repo.list_exam_options(catalog_id)
        ],
    }


def _session_depends(fn: object):
    annotation = inspect.signature(fn).parameters["session"].annotation
    return get_args(annotation)[1]


def test_write_dependencies_use_function_scoped_write_db() -> None:
    read_dep = _session_depends(get_admin_catalog_read_service)
    write_dep = _session_depends(get_admin_catalog_write_service)
    assert read_dep.dependency is get_db
    assert read_dep.scope != "function"
    assert write_dep.dependency is get_write_db
    assert write_dep.scope == "function"


def test_openapi_lists_five_catalog_routes_without_delete(
    api_client: TestClient,
) -> None:
    schema = api_client.get("/openapi.json").json()
    paths = schema["paths"]
    collection = "/api/v1/admin/admission-catalogs"
    item = "/api/v1/admin/admission-catalogs/{catalog_id}"
    status_path = "/api/v1/admin/admission-catalogs/{catalog_id}/status"
    assert set(paths[collection]) == {"get", "post"}
    assert set(paths[item]) == {"get", "put"}
    assert set(paths[status_path]) == {"patch"}
    catalog_paths = [
        path
        for path in paths
        if "/admin/admission-catalog" in path
    ]
    assert catalog_paths == [collection, item, status_path]
    assert all("delete" not in paths[path] for path in catalog_paths)
    tags = {
        tag
        for path in catalog_paths
        for operation in paths[path].values()
        for tag in operation.get("tags", [])
    }
    assert tags == {"admin-catalog"}


def test_post_shell_is_admin_visible_and_public_hidden(
    api_client: TestClient,
) -> None:
    created = api_client.post(ADMIN, json=_shell())
    assert created.status_code == 201
    body = created.json()
    catalog_id = body["id"]
    assert body["is_active"] is False
    assert body["directions"] == []
    assert body["exam_units"] == []
    assert "created_at" not in body

    detail = api_client.get(f"{ADMIN}/{catalog_id}")
    assert detail.status_code == 200
    assert detail.json()["is_active"] is False

    listing = api_client.get(
        ADMIN,
        params={"school_id": SCHOOL_A_ID, "status": "inactive", "page_size": 100},
    )
    assert listing.status_code == 200
    assert catalog_id in {item["id"] for item in listing.json()["items"]}

    public_detail = api_client.get(f"{PUBLIC}/{catalog_id}")
    assert public_detail.status_code == 404
    assert catalog_id not in _public_ids(api_client, SCHOOL_A_ID)


def test_post_reference_errors_hide_database_text(api_client: TestClient) -> None:
    missing = api_client.post(ADMIN, json=_shell(school_id=9_999_999))
    _assert_business_error(missing, 422, "invalid_reference")

    inactive = api_client.post(
        ADMIN,
        json=_shell(college_id=COLLEGE_INACTIVE_ID, study_mode="part_time"),
    )
    _assert_business_error(inactive, 422, "inactive_reference")

    other_school = api_client.post(
        ADMIN,
        json=_shell(
            college_id=COLLEGE_C_ID,
            admission_year=2034,
            study_mode="part_time",
        ),
    )
    _assert_business_error(other_school, 422, "reference_scope_mismatch")

    duplicate = api_client.post(
        ADMIN,
        json=_shell(admission_year=2027, study_mode="full_time"),
    )
    _assert_business_error(duplicate, 409, "duplicate_catalog_offering")


def test_put_inactive_aggregate_stays_hidden_from_public(
    api_client: TestClient,
) -> None:
    updated = api_client.put(
        f"{ADMIN}/{CATALOG_INACTIVE_ID}",
        json=_put(
            admission_year=2028,
            directions=[{"direction_code": "01", "direction_name": "history"}],
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {
                            "option_order": 1,
                            "exam_subject_id": SUBJECT_INACTIVE_ID,
                        }
                    ],
                }
            ],
        ),
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["is_active"] is False
    assert body["directions"][0]["direction_code"] == "01"
    assert body["exam_units"][0]["options"][0]["subject"]["is_active"] is False

    detail = api_client.get(f"{ADMIN}/{CATALOG_INACTIVE_ID}")
    assert detail.status_code == 200
    assert _subject_ids(detail.json()) == {SUBJECT_INACTIVE_ID}
    assert api_client.get(f"{PUBLIC}/{CATALOG_INACTIVE_ID}").status_code == 404


def test_put_active_aggregate_rules(api_client: TestClient) -> None:
    legal = api_client.put(
        f"{ADMIN}/{CATALOG_2026_FT_ID}",
        json=_put(
            admission_year=2026,
            directions=[{"direction_code": "01", "direction_name": "kept"}],
            exam_units=_active_units(),
        ),
    )
    assert legal.status_code == 200
    assert legal.json()["is_active"] is True
    assert _subject_ids(legal.json()) == {
        SUBJECT_NATIONAL_ID,
        SUBJECT_SCHOOL_ID,
        SUBJECT_ALT_ID,
    }

    inactive_subject = api_client.put(
        f"{ADMIN}/{CATALOG_2026_FT_ID}",
        json=_put(
            admission_year=2026,
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {
                            "option_order": 1,
                            "exam_subject_id": SUBJECT_INACTIVE_ID,
                        }
                    ],
                }
            ],
        ),
    )
    _assert_business_error(inactive_subject, 422, "inactive_reference")

    inactive_college = api_client.put(
        f"{ADMIN}/{CATALOG_2026_FT_ID}",
        json=_put(admission_year=2026, college_id=COLLEGE_INACTIVE_ID),
    )
    _assert_business_error(inactive_college, 422, "inactive_reference")

    inactive_major = api_client.put(
        f"{ADMIN}/{CATALOG_2026_FT_ID}",
        json=_put(admission_year=2026, major_id=MAJOR_INACTIVE_ID),
    )
    _assert_business_error(inactive_major, 422, "inactive_reference")

    school = api_client.post(
        f"{MASTER}/schools",
        json={"school_code": "ZZ_S103B_INACT", "name": "ZZ_S103B_InactiveSchool"},
    )
    assert school.status_code == 201
    school_id = school.json()["id"]
    college = api_client.post(
        f"{MASTER}/schools/{school_id}/colleges",
        json={"college_code": "IN", "name": "InactiveParentCollege"},
    )
    major = api_client.post(
        f"{MASTER}/schools/{school_id}/majors",
        json={
            "major_code": "ZZ_S103B_INACT_M",
            "name": "InactiveParentMajor",
            "degree_type": "academic",
        },
    )
    assert college.status_code == 201
    assert major.status_code == 201
    deactivated = api_client.patch(
        f"{MASTER}/schools/{school_id}/status",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    inactive_school = api_client.put(
        f"{ADMIN}/{CATALOG_2026_FT_ID}",
        json=_put(
            school_id=school_id,
            college_id=college.json()["id"],
            major_id=major.json()["id"],
            admission_year=2031,
            study_mode="part_time",
        ),
    )
    _assert_business_error(inactive_school, 422, "inactive_reference")

    other_subject = api_client.put(
        f"{ADMIN}/{CATALOG_SCHOOL_C_ID}",
        json=_put(
            school_id=SCHOOL_C_ID,
            college_id=COLLEGE_C_ID,
            major_id=MAJOR_C_ID,
            admission_year=2027,
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {"option_order": 1, "exam_subject_id": SUBJECT_SCHOOL_ID}
                    ],
                }
            ],
        ),
    )
    _assert_business_error(other_subject, 422, "reference_scope_mismatch")

    missing_subject = api_client.put(
        f"{ADMIN}/{CATALOG_2026_FT_ID}",
        json=_put(
            admission_year=2026,
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [{"option_order": 1, "exam_subject_id": 9_999_999}],
                }
            ],
        ),
    )
    _assert_business_error(missing_subject, 422, "invalid_reference")


def test_legacy_active_catalog_repaired_over_http(api_client: TestClient) -> None:
    repaired = api_client.put(
        f"{ADMIN}/{CATALOG_2027_ID}",
        json=_put(
            admission_year=2027,
            directions=[{"direction_code": "01", "direction_name": "kept"}],
            exam_units=_active_units(),
        ),
    )
    assert repaired.status_code == 200
    assert repaired.json()["is_active"] is True
    detail = api_client.get(f"{ADMIN}/{CATALOG_2027_ID}")
    assert detail.status_code == 200
    subjects = [
        option["subject"]
        for unit in detail.json()["exam_units"]
        for option in unit["options"]
    ]
    assert SUBJECT_INACTIVE_ID not in {subject["id"] for subject in subjects}
    assert subjects
    assert all(subject["is_active"] for subject in subjects)


def test_legacy_active_reactivate_still_rejects_inactive_subject(
    api_client: TestClient,
) -> None:
    response = api_client.patch(
        f"{ADMIN}/{CATALOG_2027_ID}/status",
        json={"is_active": True},
    )
    _assert_business_error(response, 422, "inactive_reference")
    detail = api_client.get(f"{ADMIN}/{CATALOG_2027_ID}")
    assert detail.status_code == 200
    assert detail.json()["is_active"] is True
    assert SUBJECT_INACTIVE_ID in _subject_ids(detail.json())


def test_deactivate_keeps_children_and_hides_public_detail(
    api_client: TestClient,
) -> None:
    first = api_client.patch(
        f"{ADMIN}/{CATALOG_2027_ID}/status",
        json={"is_active": False},
    )
    assert first.status_code == 200
    assert first.json()["is_active"] is False
    second = api_client.patch(
        f"{ADMIN}/{CATALOG_2027_ID}/status",
        json={"is_active": False},
    )
    assert second.status_code == 200
    detail = api_client.get(f"{ADMIN}/{CATALOG_2027_ID}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["is_active"] is False
    assert [item["direction_code"] for item in body["directions"]] == ["01", "02"]
    assert SUBJECT_INACTIVE_ID in _subject_ids(body)
    assert api_client.get(f"{PUBLIC}/{CATALOG_2027_ID}").status_code == 404


def test_shell_maintain_activate_becomes_public(api_client: TestClient) -> None:
    created = api_client.post(ADMIN, json=_shell())
    assert created.status_code == 201
    catalog_id = created.json()["id"]
    assert catalog_id not in _public_ids(api_client, SCHOOL_A_ID)

    maintained = api_client.put(
        f"{ADMIN}/{catalog_id}",
        json=_put(
            admission_year=SHELL_YEAR,
            directions=[{"direction_code": "01", "direction_name": "ready"}],
            exam_units=[
                {
                    "exam_unit": 1,
                    "options": [
                        {"option_order": 1, "exam_subject_id": SUBJECT_NATIONAL_ID}
                    ],
                }
            ],
        ),
    )
    assert maintained.status_code == 200
    assert maintained.json()["is_active"] is False
    assert api_client.get(f"{PUBLIC}/{catalog_id}").status_code == 404

    activated = api_client.patch(
        f"{ADMIN}/{catalog_id}/status",
        json={"is_active": True},
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    public_detail = api_client.get(f"{PUBLIC}/{catalog_id}")
    assert public_detail.status_code == 200
    assert public_detail.json()["id"] == catalog_id
    assert catalog_id in _public_ids(api_client, SCHOOL_A_ID)


def test_empty_aggregate_does_not_block_activation(api_client: TestClient) -> None:
    updated = api_client.put(
        f"{ADMIN}/{CATALOG_INACTIVE_ID}",
        json=_put(admission_year=2028, directions=[], exam_units=[]),
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False
    assert updated.json()["directions"] == []
    assert updated.json()["exam_units"] == []

    activated = api_client.patch(
        f"{ADMIN}/{CATALOG_INACTIVE_ID}/status",
        json={"is_active": True},
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True
    assert api_client.get(f"{PUBLIC}/{CATALOG_INACTIVE_ID}").status_code == 200
    assert CATALOG_INACTIVE_ID in _public_ids(api_client, SCHOOL_A_ID)


def test_admin_detail_keeps_inactive_subject_public_filters_it(
    api_client: TestClient,
) -> None:
    admin = api_client.get(f"{ADMIN}/{CATALOG_2027_ID}")
    assert admin.status_code == 200
    inactive = [
        option["subject"]
        for unit in admin.json()["exam_units"]
        for option in unit["options"]
        if option["subject"]["id"] == SUBJECT_INACTIVE_ID
    ]
    assert len(inactive) == 1
    assert inactive[0]["is_active"] is False

    public = api_client.get(f"{PUBLIC}/{CATALOG_2027_ID}")
    assert public.status_code == 200
    assert SUBJECT_INACTIVE_ID not in _subject_ids(public.json())


def test_admin_list_filters_pagination_and_unknown_school(
    api_client: TestClient,
) -> None:
    missing_school = api_client.get(ADMIN)
    assert missing_school.status_code == 422
    assert isinstance(missing_school.json()["detail"], list)

    everything = api_client.get(
        ADMIN,
        params={"school_id": SCHOOL_A_ID, "status": "all", "page": 1, "page_size": 2},
    )
    assert everything.status_code == 200
    body = everything.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] == 6
    assert len(body["items"]) == 2

    active = api_client.get(
        ADMIN,
        params={"school_id": SCHOOL_A_ID, "status": "active", "page_size": 100},
    )
    inactive = api_client.get(
        ADMIN,
        params={"school_id": SCHOOL_A_ID, "status": "inactive", "page_size": 100},
    )
    assert active.status_code == 200
    assert inactive.status_code == 200
    active_ids = {item["id"] for item in active.json()["items"]}
    inactive_ids = {item["id"] for item in inactive.json()["items"]}
    assert CATALOG_2027_ID in active_ids
    assert CATALOG_2027_ID not in inactive_ids
    assert inactive_ids == {CATALOG_INACTIVE_ID}
    assert active.json()["total"] == 5
    assert inactive.json()["page"] == 1
    assert inactive.json()["page_size"] == 100

    unknown = api_client.get(ADMIN, params={"school_id": 9_999_999, "status": "all"})
    assert unknown.status_code == 200
    assert unknown.json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
    }

    school = api_client.post(
        f"{MASTER}/schools",
        json={"school_code": "ZZ_S103B_LIST", "name": "ZZ_S103B_ListSchool"},
    )
    school_id = school.json()["id"]
    college = api_client.post(
        f"{MASTER}/schools/{school_id}/colleges",
        json={"name": "ListCollege"},
    )
    major = api_client.post(
        f"{MASTER}/schools/{school_id}/majors",
        json={
            "major_code": "ZZ_S103B_LIST_M",
            "name": "ListMajor",
            "degree_type": "academic",
        },
    )
    shell = api_client.post(
        ADMIN,
        json=_shell(
            school_id=school_id,
            college_id=college.json()["id"],
            major_id=major.json()["id"],
            admission_year=2033,
        ),
    )
    assert shell.status_code == 201
    catalog_id = shell.json()["id"]
    deactivated = api_client.patch(
        f"{MASTER}/schools/{school_id}/status",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    listed = api_client.get(
        ADMIN,
        params={"school_id": school_id, "status": "all"},
    )
    assert listed.status_code == 200
    assert catalog_id in {item["id"] for item in listed.json()["items"]}
    assert SCHOOL_B_INACTIVE_ID != school_id


def test_duplicate_base_put_leaves_original_aggregate(api_client: TestClient) -> None:
    before = api_client.get(f"{ADMIN}/{CATALOG_2027_ID}")
    assert before.status_code == 200
    conflict = api_client.put(
        f"{ADMIN}/{CATALOG_2027_ID}",
        json=_put(
            admission_year=2026,
            study_mode="full_time",
            directions=[{"direction_code": "99", "direction_name": "nope"}],
            exam_units=_active_units(),
        ),
    )
    _assert_business_error(conflict, 409, "duplicate_catalog_offering")
    after = api_client.get(f"{ADMIN}/{CATALOG_2027_ID}")
    assert after.status_code == 200
    assert after.json()["admission_year"] == before.json()["admission_year"]
    assert after.json()["study_mode"] == before.json()["study_mode"]
    assert after.json()["is_active"] is True
    assert after.json()["directions"] == before.json()["directions"]
    assert _subject_ids(after.json()) == _subject_ids(before.json())


def test_final_flush_failure_rolls_back_replaced_aggregate(
    seeded_session: Session,
    monkeypatch: object,
) -> None:
    seeded_session.commit()
    before = _snapshot(seeded_session, CATALOG_2027_ID)
    original_flush = AdminCatalogRepository.flush
    calls = {"n": 0}

    def tracked_flush(self: AdminCatalogRepository) -> None:
        calls["n"] += 1
        original_flush(self)
        if calls["n"] == 3:
            raise RuntimeError("forced final failure")

    monkeypatch.setattr(AdminCatalogRepository, "flush", tracked_flush)

    def _override_get_db() -> Generator[Session, None, None]:
        yield seeded_session

    def _override_get_write_db() -> Generator[Session, None, None]:
        try:
            yield seeded_session
            seeded_session.commit()
        except Exception:
            seeded_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_write_db] = _override_get_write_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.put(
                f"{ADMIN}/{CATALOG_2027_ID}",
                json=_put(
                    admission_year=2027,
                    directions=[
                        {"direction_code": "99", "direction_name": "should-rollback"}
                    ],
                    exam_units=[
                        {
                            "exam_unit": 4,
                            "options": [
                                {
                                    "option_order": 1,
                                    "exam_subject_id": SUBJECT_NATIONAL_ID,
                                }
                            ],
                        }
                    ],
                ),
            )
        assert response.status_code == 500
        assert calls["n"] == 3
        assert _snapshot(seeded_session, CATALOG_2027_ID) == before
    finally:
        app.dependency_overrides.clear()


def test_missing_catalog_is_not_found(api_client: TestClient) -> None:
    detail = api_client.get(f"{ADMIN}/9999999")
    _assert_business_error(detail, 404, "not_found")
    missing_put = api_client.put(f"{ADMIN}/9999999", json=_put())
    _assert_business_error(missing_put, 404, "not_found")
