from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import (
    CATALOG_2026_FT_ID,
    CATALOG_2027_ID,
    CATALOG_INACTIVE_ID,
    COLLEGE_A_ID,
    COLLEGE_C_ID,
    MAJOR_A_ID,
    PREFIX,
    SCHOOL_A_ID,
    SCHOOL_B_INACTIVE_ID,
    SCHOOL_D_ID,
    SCHOOL_E_ID,
    SUBJECT_INACTIVE_ID,
)

EXPECTED_PATHS = {
    "/api/v1/schools",
    "/api/v1/schools/{school_id}",
    "/api/v1/schools/{school_id}/colleges",
    "/api/v1/schools/{school_id}/majors",
    "/api/v1/schools/{school_id}/admission-years",
    "/api/v1/admission-catalogs",
    "/api/v1/admission-catalogs/{catalog_id}",
}

FORBIDDEN_PATHS = {
    "/api/v1/exam-subjects",
    "/api/v1/directions",
}

WRITE_METHODS = {"post", "put", "patch", "delete"}


def test_openapi_contains_seven_get_paths() -> None:
    response = TestClient(app).get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in EXPECTED_PATHS:
        assert path in paths
        assert "get" in paths[path]
    for path in FORBIDDEN_PATHS:
        assert path not in paths
    for path, operations in paths.items():
        if path.startswith("/api/v1"):
            assert WRITE_METHODS.isdisjoint(operations)


def _openapi_schema(spec: dict, node: dict) -> dict:
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        return spec["components"]["schemas"][name]
    return node


def test_openapi_study_mode_response_is_enum() -> None:
    spec = TestClient(app).get("/openapi.json").json()
    summary = spec["components"]["schemas"]["AdmissionCatalogSummary"]
    study_mode = _openapi_schema(spec, summary["properties"]["study_mode"])
    assert study_mode.get("enum") == ["full_time", "part_time"]


def test_list_schools_active_only_and_shape(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/schools", params={"q": PREFIX})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 4
    codes = [item["school_code"] for item in body["items"]]
    assert f"{PREFIX}_B" not in codes
    assert codes == [
        f"{PREFIX}_A",
        f"{PREFIX}_C",
        f"{PREFIX}_D",
        f"{PREFIX}_E",
    ]
    assert set(body["items"][0]) == {"id", "school_code", "name"}
    assert "is_active" not in body["items"][0]


def test_list_schools_q_and_pagination(api_client: TestClient) -> None:
    matched = api_client.get(
        "/api/v1/schools",
        params={"q": "alphauniversity"},
    )
    assert matched.status_code == 200
    assert matched.json()["total"] == 1
    assert matched.json()["items"][0]["id"] == SCHOOL_A_ID

    page = api_client.get(
        "/api/v1/schools",
        params={"q": PREFIX, "page": 2, "page_size": 2},
    )
    assert page.status_code == 200
    body = page.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 4
    assert len(body["items"]) == 2
    assert [item["id"] for item in body["items"]] == [SCHOOL_D_ID, SCHOOL_E_ID]


def test_get_school_200_and_404(api_client: TestClient) -> None:
    ok = api_client.get(f"/api/v1/schools/{SCHOOL_A_ID}")
    assert ok.status_code == 200
    assert ok.json() == {
        "id": SCHOOL_A_ID,
        "school_code": f"{PREFIX}_A",
        "name": f"{PREFIX}_AlphaUniversity",
    }

    missing = api_client.get("/api/v1/schools/9199999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "school not found"

    inactive = api_client.get(f"/api/v1/schools/{SCHOOL_B_INACTIVE_ID}")
    assert inactive.status_code == 404
    assert inactive.json()["detail"] == "school not found"


def test_list_colleges(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/schools/{SCHOOL_A_ID}/colleges")
    assert response.status_code == 200
    items = response.json()
    assert [item["college_code"] for item in items] == ["A_COL", "B_COL", None]
    assert all("is_active" not in item for item in items)

    missing = api_client.get("/api/v1/schools/9199999/colleges")
    assert missing.status_code == 404


def test_list_majors(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/schools/{SCHOOL_A_ID}/majors")
    assert response.status_code == 200
    items = response.json()
    assert [item["major_code"] for item in items] == [
        f"{PREFIX}_140500",
        f"{PREFIX}_140501",
    ]
    inactive_school = api_client.get(
        f"/api/v1/schools/{SCHOOL_B_INACTIVE_ID}/majors"
    )
    assert inactive_school.status_code == 404


def test_admission_years_distinct_desc_and_empty(api_client: TestClient) -> None:
    years = api_client.get(f"/api/v1/schools/{SCHOOL_A_ID}/admission-years")
    assert years.status_code == 200
    assert years.json() == {"items": [2027, 2026]}

    empty = api_client.get(f"/api/v1/schools/{SCHOOL_D_ID}/admission-years")
    assert empty.status_code == 200
    assert empty.json() == {"items": []}

    missing = api_client.get("/api/v1/schools/9199999/admission-years")
    assert missing.status_code == 404


def test_list_catalogs_requires_school_id(api_client: TestClient) -> None:
    missing = api_client.get("/api/v1/admission-catalogs")
    assert missing.status_code == 422

    not_int = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": "abc"},
    )
    assert not_int.status_code == 422

    non_positive = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": 0},
    )
    assert non_positive.status_code == 422


def test_list_catalogs_filters_and_empty_semantics(api_client: TestClient) -> None:
    listing = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": SCHOOL_A_ID, "page_size": 1},
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == CATALOG_2027_ID
    assert body["items"][0]["school"]["id"] == SCHOOL_A_ID
    assert "is_active" not in body["items"][0]

    year = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": SCHOOL_A_ID, "admission_year": 2026},
    )
    assert year.status_code == 200
    assert year.json()["total"] == 2

    mode = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": SCHOOL_A_ID, "study_mode": "part_time"},
    )
    assert mode.status_code == 200
    assert mode.json()["total"] == 1

    unknown = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": 9_199_999},
    )
    assert unknown.status_code == 200
    assert unknown.json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
    }

    mismatch = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": SCHOOL_A_ID, "college_id": COLLEGE_C_ID},
    )
    assert mismatch.status_code == 200
    assert mismatch.json()["total"] == 0
    assert mismatch.json()["items"] == []

    invalid_mode = api_client.get(
        "/api/v1/admission-catalogs",
        params={"school_id": SCHOOL_A_ID, "study_mode": "night"},
    )
    assert invalid_mode.status_code == 422


def test_get_catalog_detail_grouping_and_404(api_client: TestClient) -> None:
    response = api_client.get(f"/api/v1/admission-catalogs/{CATALOG_2027_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == CATALOG_2027_ID
    assert body["school"]["id"] == SCHOOL_A_ID
    assert body["college"]["id"] == COLLEGE_A_ID
    assert body["major"]["id"] == MAJOR_A_ID
    assert [item["direction_code"] for item in body["directions"]] == ["01", "02"]
    assert [unit["exam_unit"] for unit in body["exam_units"]] == [1, 2]
    assert len(body["exam_units"][0]["options"]) == 1
    assert [
        option["subject"]["subject_code"]
        for option in body["exam_units"][1]["options"]
    ] == [f"{PREFIX}_895", f"{PREFIX}_204"]
    subject_ids = [
        option["subject"]["id"]
        for unit in body["exam_units"]
        for option in unit["options"]
    ]
    assert SUBJECT_INACTIVE_ID not in subject_ids
    assert "is_active" not in body
    assert "created_at" not in body
    assert "updated_at" not in body

    empty_directions = api_client.get(
        f"/api/v1/admission-catalogs/{CATALOG_2026_FT_ID}"
    )
    assert empty_directions.status_code == 200
    assert empty_directions.json()["directions"] == []
    assert empty_directions.json()["exam_units"] == []

    missing = api_client.get("/api/v1/admission-catalogs/9199999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "admission_catalog not found"

    inactive = api_client.get(f"/api/v1/admission-catalogs/{CATALOG_INACTIVE_ID}")
    assert inactive.status_code == 404
