import inspect
from typing import get_args

from fastapi.testclient import TestClient

from app.api.admin_teacher import (
    get_admin_teacher_read_service,
    get_admin_teacher_write_service,
)
from app.core.database import get_db, get_write_db
from tests.conftest import (
    CATALOG_2026_FT_ID,
    COLLEGE_A_ID,
    MAJOR_A_ID,
    SCHOOL_A_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

PROFILES = "/api/v1/admin/teacher-profiles"
ADMISSIONS = "/api/v1/admin/admission-records"
PREFIX = "ZZ_TEST_S202_API"

_TEACHER_ROUTES = {
    "/api/v1/admin/teacher-profiles": {"get", "post"},
    "/api/v1/admin/teacher-profiles/{teacher_profile_id}": {"get", "patch"},
    "/api/v1/admin/teacher-profiles/{teacher_profile_id}/status": {"patch"},
    "/api/v1/admin/teacher-profiles/{teacher_profile_id}/availability": {"patch"},
    "/api/v1/admin/teacher-profiles/{teacher_profile_id}/verification": {"patch"},
    "/api/v1/admin/teacher-profiles/{teacher_profile_id}/admission-records": {"post"},
    "/api/v1/admin/admission-records/{admission_record_id}": {"patch"},
    "/api/v1/admin/admission-records/{admission_record_id}/status": {"patch"},
    "/api/v1/admin/teacher-profiles/{teacher_profile_id}/teach-subjects": {"put"},
}


def _session_depends(fn: object):
    annotation = inspect.signature(fn).parameters["session"].annotation
    return get_args(annotation)[1]


def _assert_business_error(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert body["detail"]["code"] == code
    assert isinstance(body["detail"]["message"], str)
    text = response.text.lower()
    assert "psycopg" not in text
    assert "sqlalchemy" not in text
    assert "duplicate key" not in text
    assert "database_url" not in text


def _assert_validation(response) -> None:
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def _create_teacher(api_client: TestClient, name: str) -> dict:
    created = api_client.post(
        PROFILES,
        json={"display_name": f"{PREFIX}_{name}", "bio": None},
    )
    assert created.status_code == 201
    return created.json()


def _admission_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "school_id": SCHOOL_A_ID,
        "college_id": COLLEGE_A_ID,
        "major_id": MAJOR_A_ID,
        "admission_year": 2025,
        "study_mode": "full_time",
    }
    body.update(overrides)
    return body


def test_read_and_write_dependencies() -> None:
    read_dep = _session_depends(get_admin_teacher_read_service)
    write_dep = _session_depends(get_admin_teacher_write_service)
    assert read_dep.dependency is get_db
    assert read_dep.scope != "function"
    assert write_dep.dependency is get_write_db
    assert write_dep.scope == "function"


def test_openapi_lists_eleven_teacher_routes_without_delete(
    api_client: TestClient,
) -> None:
    paths = api_client.get("/openapi.json").json()["paths"]
    for path, methods in _TEACHER_ROUTES.items():
        assert set(paths[path]) == methods
    teacher_paths = [
        path
        for path in paths
        if "teacher-profile" in path or "/admin/admission-records" in path
    ]
    assert set(teacher_paths) == set(_TEACHER_ROUTES)
    operations = [
        (path, method)
        for path in teacher_paths
        for method in paths[path]
    ]
    assert len(operations) == 11
    assert all("delete" not in paths[path] for path in teacher_paths)
    assert "get" not in paths["/api/v1/admin/admission-records/{admission_record_id}"]
    tags = {
        tag
        for path in teacher_paths
        for operation in paths[path].values()
        for tag in operation.get("tags", [])
    }
    assert tags == {"admin-teacher"}
    assert not any(path.startswith("/api/v1/teacher") for path in paths)


def test_public_teacher_routes_are_absent(api_client: TestClient) -> None:
    listing = api_client.get("/api/v1/teacher-profiles")
    detail = api_client.get("/api/v1/teacher-profiles/1")
    assert listing.status_code == 404
    assert detail.status_code == 404


def test_create_get_and_list_teacher(api_client: TestClient) -> None:
    name = f"{PREFIX}_Create"
    created = api_client.post(
        PROFILES,
        json={"display_name": name, "bio": None},
    )
    assert created.status_code == 201
    body = created.json()
    teacher_id = body["id"]
    assert body["display_name"] == name
    assert body["bio"] is None
    assert body["is_active"] is True
    assert body["availability_status"] == "unknown"
    assert body["verification_status"] == "unverified"
    assert body["admission_records"] == []
    assert body["teach_subjects"] == []
    for hidden in ("created_at", "updated_at", "phone", "wechat", "email"):
        assert hidden not in body

    detail = api_client.get(f"{PROFILES}/{teacher_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == teacher_id
    assert detail.json()["display_name"] == name

    listing = api_client.get(PROFILES, params={"q": name})
    assert listing.status_code == 200
    assert teacher_id in {item["id"] for item in listing.json()["items"]}


def test_teacher_header_endpoints_keep_states_orthogonal(
    api_client: TestClient,
) -> None:
    teacher_id = _create_teacher(api_client, "Header")["id"]
    renamed = api_client.patch(
        f"{PROFILES}/{teacher_id}",
        json={"display_name": f"{PREFIX}_HeaderRenamed", "bio": "short bio"},
    )
    assert renamed.status_code == 200
    summary = renamed.json()
    assert summary["display_name"] == f"{PREFIX}_HeaderRenamed"
    assert summary["bio"] == "short bio"
    assert "admission_records" not in summary
    assert "teach_subjects" not in summary

    inactive = api_client.patch(
        f"{PROFILES}/{teacher_id}/status",
        json={"is_active": False},
    )
    assert inactive.status_code == 200
    assert inactive.json()["is_active"] is False
    assert inactive.json()["availability_status"] == "unknown"
    assert "admission_records" not in inactive.json()

    availability = api_client.patch(
        f"{PROFILES}/{teacher_id}/availability",
        json={"availability_status": "available"},
    )
    assert availability.status_code == 200
    assert availability.json()["availability_status"] == "available"
    assert availability.json()["is_active"] is False

    verification = api_client.patch(
        f"{PROFILES}/{teacher_id}/verification",
        json={"verification_status": "rejected"},
    )
    assert verification.status_code == 200
    verified = verification.json()
    assert verified["verification_status"] == "rejected"
    assert verified["is_active"] is False
    assert verified["availability_status"] == "available"
    assert "admission_records" not in verified
    assert "teach_subjects" not in verified


def test_admission_create_patch_and_status(api_client: TestClient) -> None:
    teacher_id = _create_teacher(api_client, "Admission")["id"]
    created = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(final_total=70),
    )
    assert created.status_code == 201
    admission = created.json()
    admission_id = admission["id"]
    assert admission["teacher_profile_id"] == teacher_id
    assert admission["school"]["id"] == SCHOOL_A_ID
    assert admission["is_active"] is True
    assert isinstance(admission["final_total"], int | float)

    patched = api_client.patch(
        f"{ADMISSIONS}/{admission_id}",
        json={"final_total": 88.5},
    )
    assert patched.status_code == 200
    score = patched.json()["final_total"]
    assert isinstance(score, int | float)
    assert score == 88.5
    assert not isinstance(score, str)

    deactivated = api_client.patch(
        f"{ADMISSIONS}/{admission_id}/status",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert deactivated.json()["final_total"] == 88.5


def test_replace_teach_subjects_returns_detail(api_client: TestClient) -> None:
    teacher_id = _create_teacher(api_client, "Subjects")["id"]
    replaced = api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]},
    )
    assert replaced.status_code == 200
    body = replaced.json()
    assert isinstance(body, dict)
    assert "teach_subjects" in body
    assert "admission_records" in body
    assert {item["id"] for item in body["teach_subjects"]} == {
        SUBJECT_NATIONAL_ID,
        SUBJECT_SCHOOL_ID,
    }

    cleared = api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": []},
    )
    assert cleared.status_code == 200
    cleared_body = cleared.json()
    assert isinstance(cleared_body, dict)
    assert cleared_body["teach_subjects"] == []
    assert cleared_body["id"] == teacher_id


def test_business_errors_map_without_database_text(api_client: TestClient) -> None:
    missing = api_client.get(f"{PROFILES}/999999991")
    _assert_business_error(missing, 404, "not_found")

    teacher_id = _create_teacher(api_client, "InactiveParent")["id"]
    inactive = api_client.patch(
        f"{PROFILES}/{teacher_id}/status",
        json={"is_active": False},
    )
    assert inactive.status_code == 200
    rejected = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(),
    )
    _assert_business_error(rejected, 422, "parent_inactive")


def test_catalog_identity_mismatch_is_422(api_client: TestClient) -> None:
    teacher_id = _create_teacher(api_client, "CatalogMismatch")["id"]
    mismatched = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(admission_catalog_id=CATALOG_2026_FT_ID),
    )
    _assert_business_error(mismatched, 422, "catalog_identity_mismatch")


def test_query_path_and_body_validation_stay_fastapi_arrays(
    api_client: TestClient,
) -> None:
    _assert_validation(api_client.get(PROFILES, params={"page": 0}))
    _assert_validation(api_client.get(PROFILES, params={"page_size": 101}))
    _assert_validation(api_client.get(PROFILES, params={"status": "paused"}))
    _assert_validation(api_client.get(PROFILES, params={"school_id": 0}))
    _assert_validation(api_client.get(f"{PROFILES}/0"))
    _assert_validation(
        api_client.put(
            f"{PROFILES}/1/teach-subjects",
            json={
                "exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_NATIONAL_ID],
            },
        )
    )
