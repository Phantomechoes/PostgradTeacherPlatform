import inspect
from collections.abc import Generator
from typing import get_args

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin_teacher import (
    get_admin_teacher_read_service,
    get_admin_teacher_write_service,
)
from app.core.database import get_db, get_write_db
from app.main import app
from app.models import (
    AdmissionCatalog,
    AdmissionRecord,
    College,
    ExamSubject,
    Major,
    School,
    TeacherProfile,
)
from tests.conftest import (
    CATALOG_2026_FT_ID,
    CATALOG_2027_ID,
    COLLEGE_A_ID,
    COLLEGE_C_ID,
    MAJOR_A_ID,
    MAJOR_C_ID,
    SCHOOL_A_ID,
    SCHOOL_C_ID,
    SUBJECT_ALT_ID,
    SUBJECT_INACTIVE_ID,
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


def _listed(api_client: TestClient, **params: object) -> list[dict]:
    response = api_client.get(PROFILES, params={"page_size": 100, **params})
    assert response.status_code == 200
    items = response.json()["items"]
    assert all("admission_records" not in item for item in items)
    assert all("teach_subjects" not in item for item in items)
    return items


def _detail(api_client: TestClient, teacher_id: int) -> dict:
    response = api_client.get(f"{PROFILES}/{teacher_id}")
    assert response.status_code == 200
    body = response.json()
    for hidden in ("created_at", "updated_at", "phone", "wechat", "email"):
        assert hidden not in body
    return body


def _deactivate(session: Session, *pairs: tuple[type, int]) -> None:
    for model, row_id in pairs:
        row = session.get(model, row_id)
        assert row is not None
        row.is_active = False
    session.flush()


def _subject_ids(body: dict) -> set[int]:
    return {item["id"] for item in body["teach_subjects"]}


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


def test_list_requires_same_admission_row(api_client: TestClient) -> None:
    teacher_id = _create_teacher(api_client, "SameRow")["id"]
    first = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(admission_year=2026, study_mode="full_time"),
    )
    second = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(
            school_id=SCHOOL_C_ID,
            college_id=COLLEGE_C_ID,
            major_id=MAJOR_C_ID,
            admission_year=2027,
            study_mode="part_time",
        ),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    split_major = {
        item["id"]
        for item in _listed(
            api_client,
            school_id=SCHOOL_A_ID,
            major_id=MAJOR_C_ID,
        )
    }
    split_year = {
        item["id"]
        for item in _listed(
            api_client,
            school_id=SCHOOL_A_ID,
            admission_year=2027,
        )
    }
    matched = {
        item["id"]
        for item in _listed(
            api_client,
            school_id=SCHOOL_A_ID,
            college_id=COLLEGE_A_ID,
            major_id=MAJOR_A_ID,
            admission_year=2026,
            study_mode="full_time",
        )
    }
    assert teacher_id not in split_major
    assert teacher_id not in split_year
    assert teacher_id in matched


def test_inactive_admission_filters_out_but_stays_in_detail(
    api_client: TestClient,
) -> None:
    teacher_id = _create_teacher(api_client, "InactiveAdmission")["id"]
    created = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(),
    )
    assert created.status_code == 201
    admission_id = created.json()["id"]
    deactivated = api_client.patch(
        f"{ADMISSIONS}/{admission_id}/status",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    listed = {item["id"] for item in _listed(api_client, school_id=SCHOOL_A_ID)}
    assert teacher_id not in listed
    detail = _detail(api_client, teacher_id)
    assert [row["id"] for row in detail["admission_records"]] == [admission_id]
    assert detail["admission_records"][0]["is_active"] is False
    assert detail["admission_records"][0]["school"]["id"] == SCHOOL_A_ID


def test_list_q_matches_display_name_only(api_client: TestClient) -> None:
    keyword = "ZZQK202X"
    bio_only = api_client.post(
        PROFILES,
        json={
            "display_name": f"{PREFIX}_BioOnly",
            "bio": f"notes {keyword} only-in-bio",
        },
    )
    named = api_client.post(
        PROFILES,
        json={"display_name": f"{PREFIX}_{keyword}", "bio": None},
    )
    assert bio_only.status_code == 201
    assert named.status_code == 201
    bio_id = bio_only.json()["id"]
    named_id = named.json()["id"]
    exact = {item["id"] for item in _listed(api_client, q=keyword)}
    padded = {item["id"] for item in _listed(api_client, q=f"  {keyword}  ")}
    assert exact == {named_id}
    assert padded == {named_id}
    blank = api_client.get(PROFILES, params={"q": "   ", "page_size": 100})
    plain = api_client.get(PROFILES, params={"page_size": 100})
    assert blank.status_code == 200
    assert plain.status_code == 200
    assert blank.json()["total"] == plain.json()["total"]
    assert {bio_id, named_id} <= {item["id"] for item in blank.json()["items"]}


def test_list_filters_status_availability_and_verification(
    api_client: TestClient,
) -> None:
    available = _create_teacher(api_client, "FilterAvailable")["id"]
    rejected = _create_teacher(api_client, "FilterRejected")["id"]
    untouched = _create_teacher(api_client, "FilterUntouched")["id"]
    assert api_client.patch(
        f"{PROFILES}/{available}/availability",
        json={"availability_status": "available"},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{available}/verification",
        json={"verification_status": "verified"},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{rejected}/status",
        json={"is_active": False},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{rejected}/availability",
        json={"availability_status": "unavailable"},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{rejected}/verification",
        json={"verification_status": "rejected"},
    ).status_code == 200
    everyone = {item["id"] for item in _listed(api_client)}
    assert {available, rejected, untouched} <= everyone
    active = {item["id"] for item in _listed(api_client, status="active")}
    inactive = {item["id"] for item in _listed(api_client, status="inactive")}
    assert {available, untouched} <= active
    assert rejected not in active
    assert rejected in inactive
    assert available not in inactive
    assert {item["id"] for item in _listed(api_client, availability="available")} == {
        available
    }
    assert {item["id"] for item in _listed(api_client, verification="verified")} == {
        available
    }
    assert {item["id"] for item in _listed(api_client, verification="rejected")} == {
        rejected
    }


def test_admission_patch_uses_effective_target(
    api_client: TestClient,
    seeded_session: Session,
) -> None:
    year_teacher = _create_teacher(api_client, "PatchYear")["id"]
    linked = api_client.post(
        f"{PROFILES}/{year_teacher}/admission-records",
        json=_admission_body(
            admission_year=2026,
            admission_catalog_id=CATALOG_2026_FT_ID,
        ),
    )
    assert linked.status_code == 201
    mismatched = api_client.patch(
        f"{ADMISSIONS}/{linked.json()['id']}",
        json={"admission_year": 2027},
    )
    _assert_business_error(mismatched, 422, "catalog_identity_mismatch")
    kept = _detail(api_client, year_teacher)["admission_records"][0]
    assert kept["admission_year"] == 2026
    assert kept["admission_catalog_id"] == CATALOG_2026_FT_ID

    clear_teacher = _create_teacher(api_client, "PatchNull")["id"]
    created = api_client.post(
        f"{PROFILES}/{clear_teacher}/admission-records",
        json=_admission_body(
            admission_year=2027,
            admission_catalog_id=CATALOG_2027_ID,
            initial_total=12.5,
        ),
    )
    assert created.status_code == 201
    cleared = api_client.patch(
        f"{ADMISSIONS}/{created.json()['id']}",
        json={"initial_total": None, "admission_catalog_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["initial_total"] is None
    assert cleared.json()["admission_catalog_id"] is None
    assert isinstance(cleared.json()["final_total"], int | float | type(None))

    score_teacher = _create_teacher(api_client, "PatchInactiveRef")["id"]
    original = api_client.post(
        f"{PROFILES}/{score_teacher}/admission-records",
        json=_admission_body(final_total=70),
    )
    assert original.status_code == 201
    _deactivate(
        seeded_session,
        (School, SCHOOL_A_ID),
        (College, COLLEGE_A_ID),
        (Major, MAJOR_A_ID),
    )
    updated = api_client.patch(
        f"{ADMISSIONS}/{original.json()['id']}",
        json={"final_total": 88},
    )
    assert updated.status_code == 200
    assert isinstance(updated.json()["final_total"], int | float)
    assert updated.json()["final_total"] == 88
    assert updated.json()["school"]["id"] == SCHOOL_A_ID
    assert updated.json()["school"]["is_active"] is False


def test_reactivate_allows_inactive_refs_and_inactive_teacher(
    api_client: TestClient,
    seeded_session: Session,
) -> None:
    teacher_id = _create_teacher(api_client, "Reactivate")["id"]
    created = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(
            admission_year=2026,
            admission_catalog_id=CATALOG_2026_FT_ID,
        ),
    )
    assert created.status_code == 201
    admission_id = created.json()["id"]
    assert api_client.patch(
        f"{ADMISSIONS}/{admission_id}/status",
        json={"is_active": False},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{teacher_id}/status",
        json={"is_active": False},
    ).status_code == 200
    _deactivate(
        seeded_session,
        (School, SCHOOL_A_ID),
        (College, COLLEGE_A_ID),
        (Major, MAJOR_A_ID),
        (AdmissionCatalog, CATALOG_2026_FT_ID),
    )
    restored = api_client.patch(
        f"{ADMISSIONS}/{admission_id}/status",
        json={"is_active": True},
    )
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True
    assert restored.json()["admission_catalog_id"] == CATALOG_2026_FT_ID
    assert isinstance(restored.json()["final_total"], int | float | type(None))
    detail = _detail(api_client, teacher_id)
    assert detail["is_active"] is False
    assert detail["admission_records"][0]["is_active"] is True
    assert detail["admission_records"][0]["school"]["is_active"] is False


def test_reactivate_rejects_catalog_identity_mismatch(
    api_client: TestClient,
    seeded_session: Session,
) -> None:
    teacher_id = _create_teacher(api_client, "ReactivateMismatch")["id"]
    created = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(
            admission_year=2026,
            admission_catalog_id=CATALOG_2026_FT_ID,
        ),
    )
    assert created.status_code == 201
    admission_id = created.json()["id"]
    assert api_client.patch(
        f"{ADMISSIONS}/{admission_id}/status",
        json={"is_active": False},
    ).status_code == 200
    stored = seeded_session.get(AdmissionRecord, admission_id)
    assert stored is not None
    stored.admission_year = 2024
    seeded_session.flush()
    rejected = api_client.patch(
        f"{ADMISSIONS}/{admission_id}/status",
        json={"is_active": True},
    )
    _assert_business_error(rejected, 422, "catalog_identity_mismatch")
    detail = _detail(api_client, teacher_id)
    assert detail["admission_records"][0]["id"] == admission_id
    assert detail["admission_records"][0]["is_active"] is False


def test_inactive_teacher_can_keep_or_remove_subjects_but_not_add(
    api_client: TestClient,
) -> None:
    removable = _create_teacher(api_client, "D7Remove")["id"]
    assert api_client.put(
        f"{PROFILES}/{removable}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{removable}/status",
        json={"is_active": False},
    ).status_code == 200
    removed = api_client.put(
        f"{PROFILES}/{removable}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID]},
    )
    assert removed.status_code == 200
    assert isinstance(removed.json(), dict)
    assert _subject_ids(removed.json()) == {SUBJECT_NATIONAL_ID}

    kept_teacher = _create_teacher(api_client, "D7Keep")["id"]
    assert api_client.put(
        f"{PROFILES}/{kept_teacher}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{kept_teacher}/status",
        json={"is_active": False},
    ).status_code == 200
    kept = api_client.put(
        f"{PROFILES}/{kept_teacher}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]},
    )
    assert kept.status_code == 200
    assert _subject_ids(kept.json()) == {SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID}
    rejected = api_client.put(
        f"{PROFILES}/{kept_teacher}/teach-subjects",
        json={
            "exam_subject_ids": [
                SUBJECT_NATIONAL_ID,
                SUBJECT_SCHOOL_ID,
                SUBJECT_ALT_ID,
            ]
        },
    )
    _assert_business_error(rejected, 422, "parent_inactive")
    assert _subject_ids(_detail(api_client, kept_teacher)) == {
        SUBJECT_NATIONAL_ID,
        SUBJECT_SCHOOL_ID,
    }


def test_missing_subject_precedes_parent_inactive(api_client: TestClient) -> None:
    teacher_id = _create_teacher(api_client, "D7Missing")["id"]
    assert api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID]},
    ).status_code == 200
    assert api_client.patch(
        f"{PROFILES}/{teacher_id}/status",
        json={"is_active": False},
    ).status_code == 200
    missing_id = 9_999_993
    rejected = api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, missing_id]},
    )
    _assert_business_error(rejected, 422, "invalid_reference")
    assert str(missing_id) in rejected.json()["detail"]["message"]
    assert _subject_ids(_detail(api_client, teacher_id)) == {SUBJECT_NATIONAL_ID}


def test_d12_inactive_subject_rules(
    api_client: TestClient,
    seeded_session: Session,
) -> None:
    teacher_id = _create_teacher(api_client, "D12Rules")["id"]
    created = api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]},
    )
    assert created.status_code == 200
    _deactivate(seeded_session, (ExamSubject, SUBJECT_SCHOOL_ID))
    kept = api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]},
    )
    assert kept.status_code == 200
    kept_flags = {item["id"]: item["is_active"] for item in kept.json()["teach_subjects"]}
    assert kept_flags[SUBJECT_SCHOOL_ID] is False
    assert kept_flags[SUBJECT_NATIONAL_ID] is True
    removed = api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID]},
    )
    assert removed.status_code == 200
    assert _subject_ids(removed.json()) == {SUBJECT_NATIONAL_ID}
    rejected = api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_INACTIVE_ID]},
    )
    _assert_business_error(rejected, 422, "inactive_reference")
    assert _subject_ids(_detail(api_client, teacher_id)) == {SUBJECT_NATIONAL_ID}


def test_duplicate_admission_is_conflict(api_client: TestClient) -> None:
    teacher_id = _create_teacher(api_client, "DuplicateAdmission")["id"]
    body = _admission_body(admission_year=2024)
    first = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=body,
    )
    assert first.status_code == 201
    assert isinstance(first.json()["final_total"], int | float | type(None))
    second = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=body,
    )
    _assert_business_error(second, 409, "duplicate_admission")
    assert "insert into" not in second.text.lower()


def test_write_commit_failure_happens_before_success_response(
    seeded_session: Session,
) -> None:
    seeded_session.commit()
    name = f"{PREFIX}_CommitFail"

    def _override_get_db() -> Generator[Session, None, None]:
        yield seeded_session

    def _failing_write_db() -> Generator[Session, None, None]:
        yield seeded_session
        raise RuntimeError("commit failed")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_write_db] = _failing_write_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                PROFILES,
                json={"display_name": name, "bio": None},
            )
        assert response.status_code == 500
        assert response.status_code != 201
        seeded_session.rollback()
        seeded_session.expire_all()
        found = seeded_session.scalars(
            select(TeacherProfile).where(TeacherProfile.display_name == name)
        ).all()
        assert found == []
    finally:
        seeded_session.rollback()
        app.dependency_overrides.clear()


def test_detail_returns_inactive_admission_and_subject(
    api_client: TestClient,
    seeded_session: Session,
) -> None:
    teacher_id = _create_teacher(api_client, "DetailContract")["id"]
    active = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(admission_year=2024, final_total=90),
    )
    inactive = api_client.post(
        f"{PROFILES}/{teacher_id}/admission-records",
        json=_admission_body(admission_year=2023),
    )
    assert active.status_code == 201
    assert inactive.status_code == 201
    assert isinstance(active.json()["final_total"], int | float)
    assert api_client.patch(
        f"{ADMISSIONS}/{inactive.json()['id']}/status",
        json={"is_active": False},
    ).status_code == 200
    assert api_client.put(
        f"{PROFILES}/{teacher_id}/teach-subjects",
        json={"exam_subject_ids": [SUBJECT_NATIONAL_ID, SUBJECT_SCHOOL_ID]},
    ).status_code == 200
    _deactivate(seeded_session, (ExamSubject, SUBJECT_SCHOOL_ID))
    detail = _detail(api_client, teacher_id)
    rows = {row["id"]: row for row in detail["admission_records"]}
    assert rows[active.json()["id"]]["is_active"] is True
    assert rows[inactive.json()["id"]]["is_active"] is False
    assert rows[active.json()["id"]]["school"]["id"] == SCHOOL_A_ID
    assert rows[active.json()["id"]]["college"]["id"] == COLLEGE_A_ID
    assert rows[active.json()["id"]]["major"]["id"] == MAJOR_A_ID
    flags = {item["id"]: item["is_active"] for item in detail["teach_subjects"]}
    assert flags[SUBJECT_NATIONAL_ID] is True
    assert flags[SUBJECT_SCHOOL_ID] is False

