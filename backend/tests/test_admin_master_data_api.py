from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import engine, get_db, get_write_db
from app.main import app
from app.models import School
from tests.conftest import (
    COLLEGE_INACTIVE_ID,
    MAJOR_A_ID,
    PREFIX,
    SCHOOL_A_ID,
    SCHOOL_B_INACTIVE_ID,
    SCHOOL_C_ID,
    SUBJECT_NATIONAL_ID,
    SUBJECT_SCHOOL_ID,
)

ADMIN = "/api/v1/admin"
PUBLIC = "/api/v1"
WRITE_PREFIX = "ZZ_TEST_S103A"
LEAK_CODE = f"{WRITE_PREFIX}_LEAK"


def _detail_code(response) -> str:
    return response.json()["detail"]["code"]


def test_admin_school_q_is_trimmed_like_s1_02(api_client: TestClient) -> None:
    padded = api_client.get(
        f"{ADMIN}/schools",
        params={"q": "  AlphaUniversity  "},
    )
    assert padded.status_code == 200
    ids = {item["id"] for item in padded.json()["items"]}
    assert SCHOOL_A_ID in ids

    blank = api_client.get(f"{ADMIN}/schools", params={"q": "   "})
    unfiltered = api_client.get(f"{ADMIN}/schools")
    assert blank.status_code == 200
    assert unfiltered.status_code == 200
    assert blank.json()["total"] == unfiltered.json()["total"]
    assert SCHOOL_A_ID in {item["id"] for item in blank.json()["items"]}


def test_write_commit_failure_happens_before_success_response(
    seeded_session: Session,
) -> None:
    seeded_session.commit()

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
                f"{ADMIN}/schools",
                json={
                    "school_code": f"{WRITE_PREFIX}_COMMITFAIL",
                    "name": f"{WRITE_PREFIX}_CommitFail",
                },
            )
        assert response.status_code != 201
        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()


def test_national_exam_subject_path_is_not_parsed_as_id(api_client: TestClient) -> None:
    response = api_client.get(f"{ADMIN}/exam-subjects/national")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert all(item["school_id"] is None for item in body)


def test_admin_happy_path_create_and_list(api_client: TestClient) -> None:
    school = api_client.post(
        f"{ADMIN}/schools",
        json={"school_code": f"{WRITE_PREFIX}_HP", "name": f"{WRITE_PREFIX}_Happy"},
    )
    assert school.status_code == 201
    school_body = school.json()
    school_id = school_body["id"]
    assert school_body["is_active"] is True
    assert "created_at" not in school_body
    assert "updated_at" not in school_body

    fetched = api_client.get(f"{ADMIN}/schools/{school_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == school_id

    college = api_client.post(
        f"{ADMIN}/schools/{school_id}/colleges",
        json={"college_code": "HP", "name": f"{WRITE_PREFIX}_COL"},
    )
    assert college.status_code == 201
    assert college.json()["school_id"] == school_id

    major = api_client.post(
        f"{ADMIN}/schools/{school_id}/majors",
        json={
            "major_code": f"{WRITE_PREFIX}_140600",
            "name": f"{WRITE_PREFIX}_MAJ",
            "degree_type": "academic",
        },
    )
    assert major.status_code == 201

    national = api_client.post(
        f"{ADMIN}/exam-subjects/national",
        json={"subject_code": f"{WRITE_PREFIX}_301", "name": f"{WRITE_PREFIX}_NAT"},
    )
    assert national.status_code == 201
    assert national.json()["school_id"] is None

    school_subject = api_client.post(
        f"{ADMIN}/schools/{school_id}/exam-subjects",
        json={"subject_code": f"{WRITE_PREFIX}_897", "name": f"{WRITE_PREFIX}_SCH"},
    )
    assert school_subject.status_code == 201
    assert school_subject.json()["school_id"] == school_id

    listed = api_client.get(f"{ADMIN}/schools", params={"q": f"{WRITE_PREFIX}_HP"})
    assert listed.status_code == 200
    assert any(item["id"] == school_id for item in listed.json()["items"])


def test_inactive_school_admin_vs_public(api_client: TestClient) -> None:
    deactivated = api_client.patch(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/status",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    admin_get = api_client.get(f"{ADMIN}/schools/{SCHOOL_A_ID}")
    assert admin_get.status_code == 200
    assert admin_get.json()["is_active"] is False

    public_hidden = api_client.get(f"{PUBLIC}/schools/{SCHOOL_A_ID}")
    assert public_hidden.status_code == 404

    patched = api_client.patch(
        f"{ADMIN}/schools/{SCHOOL_A_ID}",
        json={"name": f"{WRITE_PREFIX}_StillEditable"},
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False

    restored = api_client.patch(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/status",
        json={"is_active": True},
    )
    assert restored.status_code == 200
    public_visible = api_client.get(f"{PUBLIC}/schools/{SCHOOL_A_ID}")
    assert public_visible.status_code == 200


def test_inactive_parent_get_children_ok_create_rejected(api_client: TestClient) -> None:
    colleges = api_client.get(f"{ADMIN}/schools/{SCHOOL_B_INACTIVE_ID}/colleges")
    assert colleges.status_code == 200

    create_college = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_B_INACTIVE_ID}/colleges",
        json={"name": f"{WRITE_PREFIX}_NO"},
    )
    assert create_college.status_code == 422
    assert _detail_code(create_college) == "parent_inactive"

    create_major = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_B_INACTIVE_ID}/majors",
        json={
            "major_code": f"{WRITE_PREFIX}_X",
            "name": "no",
            "degree_type": "academic",
        },
    )
    assert create_major.status_code == 422
    assert _detail_code(create_major) == "parent_inactive"

    patched_child = api_client.patch(
        f"{ADMIN}/colleges/{COLLEGE_INACTIVE_ID}",
        json={"name": f"{WRITE_PREFIX}_ChildOk"},
    )
    assert patched_child.status_code == 200


def test_duplicate_school_code_rolls_back_patch(api_client: TestClient) -> None:
    conflict = api_client.patch(
        f"{ADMIN}/schools/{SCHOOL_C_ID}",
        json={"school_code": f"{PREFIX}_A"},
    )
    assert conflict.status_code == 409
    assert _detail_code(conflict) == "duplicate_school_code"

    after = api_client.get(f"{ADMIN}/schools/{SCHOOL_C_ID}")
    assert after.status_code == 200
    assert after.json()["school_code"] == f"{PREFIX}_C"


def test_duplicate_conflicts(api_client: TestClient) -> None:
    school = api_client.post(
        f"{ADMIN}/schools",
        json={"school_code": f"{PREFIX}_A", "name": "dup"},
    )
    assert school.status_code == 409
    assert _detail_code(school) == "duplicate_school_code"

    college = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/colleges",
        json={"college_code": "A_COL", "name": "dup"},
    )
    assert college.status_code == 409
    assert _detail_code(college) == "duplicate_college_code"

    major = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/majors",
        json={
            "major_code": f"{PREFIX}_140500",
            "name": "dup",
            "degree_type": "academic",
        },
    )
    assert major.status_code == 409
    assert _detail_code(major) == "duplicate_major_code"

    national = api_client.post(
        f"{ADMIN}/exam-subjects/national",
        json={"subject_code": f"{PREFIX}_101", "name": "dup"},
    )
    assert national.status_code == 409
    assert _detail_code(national) == "duplicate_national_subject_code"

    school_subject = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/exam-subjects",
        json={"subject_code": f"{PREFIX}_895", "name": "dup"},
    )
    assert school_subject.status_code == 409
    assert _detail_code(school_subject) == "duplicate_school_subject_code"

    other_school = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_C_ID}/exam-subjects",
        json={"subject_code": f"{PREFIX}_895", "name": "allowed"},
    )
    assert other_school.status_code == 201
    assert other_school.json()["school_id"] == SCHOOL_C_ID


def test_null_college_codes_are_not_duplicates(api_client: TestClient) -> None:
    first = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/colleges",
        json={"name": f"{WRITE_PREFIX}_NULL1"},
    )
    second = api_client.post(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/colleges",
        json={"college_code": None, "name": f"{WRITE_PREFIX}_NULL2"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["college_code"] is None
    assert second.json()["college_code"] is None
    assert first.json()["id"] != second.json()["id"]


def test_exam_subject_scope_and_extra_school_id(api_client: TestClient) -> None:
    national = api_client.get(f"{ADMIN}/exam-subjects/{SUBJECT_NATIONAL_ID}")
    assert national.status_code == 200
    assert national.json()["school_id"] is None

    school_subject = api_client.get(f"{ADMIN}/exam-subjects/{SUBJECT_SCHOOL_ID}")
    assert school_subject.json()["school_id"] == SCHOOL_A_ID

    extra = api_client.patch(
        f"{ADMIN}/exam-subjects/{SUBJECT_NATIONAL_ID}",
        json={"name": "x", "school_id": SCHOOL_A_ID},
    )
    assert extra.status_code == 422
    assert isinstance(extra.json()["detail"], list)

    renamed = api_client.patch(
        f"{ADMIN}/exam-subjects/{SUBJECT_NATIONAL_ID}",
        json={"name": f"{WRITE_PREFIX}_NAT2"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["school_id"] is None


def test_explicit_null_patch_semantics(api_client: TestClient) -> None:
    assert (
        api_client.patch(
            f"{ADMIN}/schools/{SCHOOL_A_ID}",
            json={"name": None},
        ).status_code
        == 422
    )
    assert (
        api_client.patch(
            f"{ADMIN}/colleges/{COLLEGE_INACTIVE_ID}",
            json={"name": None},
        ).status_code
        == 422
    )
    cleared = api_client.patch(
        f"{ADMIN}/colleges/{COLLEGE_INACTIVE_ID}",
        json={"college_code": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["college_code"] is None
    assert (
        api_client.patch(
            f"{ADMIN}/majors/{MAJOR_A_ID}",
            json={"major_code": None},
        ).status_code
        == 422
    )
    assert (
        api_client.patch(
            f"{ADMIN}/majors/{MAJOR_A_ID}",
            json={"degree_type": None},
        ).status_code
        == 422
    )
    assert (
        api_client.patch(
            f"{ADMIN}/exam-subjects/{SUBJECT_NATIONAL_ID}",
            json={"subject_code": None},
        ).status_code
        == 422
    )


def test_empty_patch_and_status_extra_field(api_client: TestClient) -> None:
    empty = api_client.patch(f"{ADMIN}/schools/{SCHOOL_A_ID}", json={})
    assert empty.status_code == 422
    assert _detail_code(empty) == "empty_patch"

    extra = api_client.patch(
        f"{ADMIN}/schools/{SCHOOL_A_ID}/status",
        json={"is_active": False, "name": "nope"},
    )
    assert extra.status_code == 422
    assert isinstance(extra.json()["detail"], list)


def test_write_is_visible_then_not_leaked_to_real_db(api_client: TestClient) -> None:
    created = api_client.post(
        f"{ADMIN}/schools",
        json={"school_code": LEAK_CODE, "name": f"{WRITE_PREFIX}_Leak"},
    )
    assert created.status_code == 201
    school_id = created.json()["id"]
    assert api_client.get(f"{ADMIN}/schools/{school_id}").status_code == 200

    with engine.connect() as connection:
        leaked = connection.execute(
            select(School.id).where(School.school_code == LEAK_CODE)
        ).first()
    assert leaked is None


def test_admin_openapi_has_paths_and_no_delete(api_client: TestClient) -> None:
    spec = api_client.get("/openapi.json").json()
    paths = spec["paths"]
    assert f"{ADMIN}/exam-subjects/national" in paths
    assert f"{ADMIN}/schools" in paths
    for path, methods in paths.items():
        if path.startswith(f"{ADMIN}/"):
            assert "delete" not in methods


def test_public_schools_list_contract_unchanged(api_client: TestClient) -> None:
    response = api_client.get(f"{PUBLIC}/schools")
    assert response.status_code == 200
    item = next(i for i in response.json()["items"] if i["id"] == SCHOOL_A_ID)
    assert "is_active" not in item
    assert api_client.get(f"{PUBLIC}/admission-catalogs", params={"school_id": SCHOOL_A_ID}).status_code == 200
