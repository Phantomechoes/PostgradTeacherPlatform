from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import engine, get_db, get_write_db
from app.main import app
from app.models import (
    AdmissionCatalog,
    AdmissionCatalogDirection,
    AdmissionCatalogExamSubject,
    College,
    ExamSubject,
    Major,
    School,
)

PREFIX = "ZZ_TEST_S102"

SCHOOL_A_ID = 9_100_001
SCHOOL_B_INACTIVE_ID = 9_100_002
SCHOOL_C_ID = 9_100_003
SCHOOL_D_ID = 9_100_004
SCHOOL_E_ID = 9_100_005

COLLEGE_A_ID = 9_100_101
COLLEGE_B_ID = 9_100_102
COLLEGE_NULL_ID = 9_100_103
COLLEGE_INACTIVE_ID = 9_100_104
COLLEGE_C_ID = 9_100_105

MAJOR_A_ID = 9_100_201
MAJOR_A2_ID = 9_100_202
MAJOR_INACTIVE_ID = 9_100_203
MAJOR_C_ID = 9_100_204

CATALOG_2027_ID = 9_100_301
CATALOG_2026_FT_ID = 9_100_302
CATALOG_2026_PT_ID = 9_100_303
CATALOG_INACTIVE_ID = 9_100_304
CATALOG_INACTIVE_COLLEGE_ID = 9_100_305
CATALOG_INACTIVE_MAJOR_ID = 9_100_306
CATALOG_SCHOOL_C_ID = 9_100_307

DIRECTION_01_ID = 9_100_401
DIRECTION_02_ID = 9_100_402

SUBJECT_NATIONAL_ID = 9_100_501
SUBJECT_SCHOOL_ID = 9_100_502
SUBJECT_INACTIVE_ID = 9_100_503
SUBJECT_ALT_ID = 9_100_504

LINK_UNIT1_ID = 9_100_601
LINK_UNIT2_OPT1_ID = 9_100_602
LINK_UNIT2_OPT2_ID = 9_100_603
LINK_INACTIVE_SUBJECT_ID = 9_100_604


def seed_master_data(session: Session) -> None:
    # Composite FKs are table-level constraints, not ORM relationships, so
    # SQLAlchemy cannot order inserts automatically. Flush by parent first.
    session.add_all(
        [
            School(
                id=SCHOOL_A_ID,
                school_code=f"{PREFIX}_A",
                name=f"{PREFIX}_AlphaUniversity",
                is_active=True,
            ),
            School(
                id=SCHOOL_B_INACTIVE_ID,
                school_code=f"{PREFIX}_B",
                name=f"{PREFIX}_BetaInactive",
                is_active=False,
            ),
            School(
                id=SCHOOL_C_ID,
                school_code=f"{PREFIX}_C",
                name=f"{PREFIX}_CharlieUniversity",
                is_active=True,
            ),
            School(
                id=SCHOOL_D_ID,
                school_code=f"{PREFIX}_D",
                name=f"{PREFIX}_DeltaUniversity",
                is_active=True,
            ),
            School(
                id=SCHOOL_E_ID,
                school_code=f"{PREFIX}_E",
                name=f"{PREFIX}_EchoUniversity",
                is_active=True,
            ),
        ]
    )
    session.flush()
    session.add_all(
        [
            College(
                id=COLLEGE_A_ID,
                school_id=SCHOOL_A_ID,
                college_code="A_COL",
                name=f"{PREFIX}_COLLEGE_A",
                is_active=True,
            ),
            College(
                id=COLLEGE_B_ID,
                school_id=SCHOOL_A_ID,
                college_code="B_COL",
                name=f"{PREFIX}_COLLEGE_B",
                is_active=True,
            ),
            College(
                id=COLLEGE_NULL_ID,
                school_id=SCHOOL_A_ID,
                college_code=None,
                name=f"{PREFIX}_COLLEGE_NULL",
                is_active=True,
            ),
            College(
                id=COLLEGE_INACTIVE_ID,
                school_id=SCHOOL_A_ID,
                college_code="Z_COL",
                name=f"{PREFIX}_COLLEGE_INACTIVE",
                is_active=False,
            ),
            College(
                id=COLLEGE_C_ID,
                school_id=SCHOOL_C_ID,
                college_code="C_COL",
                name=f"{PREFIX}_COLLEGE_C",
                is_active=True,
            ),
            Major(
                id=MAJOR_A_ID,
                school_id=SCHOOL_A_ID,
                major_code=f"{PREFIX}_140500",
                name=f"{PREFIX}_MAJOR_A",
                degree_type="academic",
                is_active=True,
            ),
            Major(
                id=MAJOR_A2_ID,
                school_id=SCHOOL_A_ID,
                major_code=f"{PREFIX}_140501",
                name=f"{PREFIX}_MAJOR_A2",
                degree_type="professional",
                is_active=True,
            ),
            Major(
                id=MAJOR_INACTIVE_ID,
                school_id=SCHOOL_A_ID,
                major_code=f"{PREFIX}_140599",
                name=f"{PREFIX}_MAJOR_INACTIVE",
                degree_type="academic",
                is_active=False,
            ),
            Major(
                id=MAJOR_C_ID,
                school_id=SCHOOL_C_ID,
                major_code=f"{PREFIX}_140500",
                name=f"{PREFIX}_MAJOR_C",
                degree_type="academic",
                is_active=True,
            ),
            ExamSubject(
                id=SUBJECT_NATIONAL_ID,
                school_id=None,
                subject_code=f"{PREFIX}_101",
                name=f"{PREFIX}_NATIONAL",
                is_active=True,
            ),
            ExamSubject(
                id=SUBJECT_SCHOOL_ID,
                school_id=SCHOOL_A_ID,
                subject_code=f"{PREFIX}_895",
                name=f"{PREFIX}_SCHOOL_SUBJECT",
                is_active=True,
            ),
            ExamSubject(
                id=SUBJECT_INACTIVE_ID,
                school_id=SCHOOL_A_ID,
                subject_code=f"{PREFIX}_999",
                name=f"{PREFIX}_INACTIVE_SUBJECT",
                is_active=False,
            ),
            ExamSubject(
                id=SUBJECT_ALT_ID,
                school_id=SCHOOL_A_ID,
                subject_code=f"{PREFIX}_204",
                name=f"{PREFIX}_ALT_SUBJECT",
                is_active=True,
            ),
        ]
    )
    session.flush()
    session.add_all(
        [
            AdmissionCatalog(
                id=CATALOG_2027_ID,
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_A_ID,
                major_id=MAJOR_A_ID,
                admission_year=2027,
                study_mode="full_time",
                is_active=True,
            ),
            AdmissionCatalog(
                id=CATALOG_2026_FT_ID,
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_A_ID,
                major_id=MAJOR_A_ID,
                admission_year=2026,
                study_mode="full_time",
                is_active=True,
            ),
            AdmissionCatalog(
                id=CATALOG_2026_PT_ID,
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_A_ID,
                major_id=MAJOR_A_ID,
                admission_year=2026,
                study_mode="part_time",
                is_active=True,
            ),
            AdmissionCatalog(
                id=CATALOG_INACTIVE_ID,
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_A_ID,
                major_id=MAJOR_A_ID,
                admission_year=2028,
                study_mode="full_time",
                is_active=False,
            ),
            AdmissionCatalog(
                id=CATALOG_INACTIVE_COLLEGE_ID,
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_INACTIVE_ID,
                major_id=MAJOR_A_ID,
                admission_year=2024,
                study_mode="full_time",
                is_active=True,
            ),
            AdmissionCatalog(
                id=CATALOG_INACTIVE_MAJOR_ID,
                school_id=SCHOOL_A_ID,
                college_id=COLLEGE_A_ID,
                major_id=MAJOR_INACTIVE_ID,
                admission_year=2023,
                study_mode="full_time",
                is_active=True,
            ),
            AdmissionCatalog(
                id=CATALOG_SCHOOL_C_ID,
                school_id=SCHOOL_C_ID,
                college_id=COLLEGE_C_ID,
                major_id=MAJOR_C_ID,
                admission_year=2027,
                study_mode="full_time",
                is_active=True,
            ),
        ]
    )
    session.flush()
    session.add_all(
        [
            AdmissionCatalogDirection(
                id=DIRECTION_01_ID,
                admission_catalog_id=CATALOG_2027_ID,
                direction_code="01",
                direction_name=f"{PREFIX}_DIR_01",
            ),
            AdmissionCatalogDirection(
                id=DIRECTION_02_ID,
                admission_catalog_id=CATALOG_2027_ID,
                direction_code="02",
                direction_name=f"{PREFIX}_DIR_02",
            ),
            AdmissionCatalogExamSubject(
                id=LINK_UNIT1_ID,
                admission_catalog_id=CATALOG_2027_ID,
                exam_subject_id=SUBJECT_NATIONAL_ID,
                exam_unit=1,
                option_order=1,
            ),
            AdmissionCatalogExamSubject(
                id=LINK_UNIT2_OPT1_ID,
                admission_catalog_id=CATALOG_2027_ID,
                exam_subject_id=SUBJECT_SCHOOL_ID,
                exam_unit=2,
                option_order=1,
            ),
            AdmissionCatalogExamSubject(
                id=LINK_UNIT2_OPT2_ID,
                admission_catalog_id=CATALOG_2027_ID,
                exam_subject_id=SUBJECT_ALT_ID,
                exam_unit=2,
                option_order=2,
            ),
            AdmissionCatalogExamSubject(
                id=LINK_INACTIVE_SUBJECT_ID,
                admission_catalog_id=CATALOG_2027_ID,
                exam_subject_id=SUBJECT_INACTIVE_ID,
                exam_unit=3,
                option_order=1,
            ),
        ]
    )
    session.flush()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        try:
            session.close()
        finally:
            transaction.rollback()
            connection.close()


@pytest.fixture
def seeded_session(db_session: Session) -> Session:
    seed_master_data(db_session)
    return db_session


@pytest.fixture
def api_client(seeded_session: Session) -> Generator[TestClient, None, None]:
    # Commit the seed SAVEPOINT so a later write-request rollback
    # cannot undo fixture data. The outer connection transaction
    # still rolls back everything when the test ends.
    seeded_session.commit()

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
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
