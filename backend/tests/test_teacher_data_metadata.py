from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Numeric,
    SmallInteger,
    String,
    Text,
    inspect,
)
from sqlalchemy.sql.schema import ForeignKeyConstraint, UniqueConstraint

from app.core.db_base import Base
from app.models import AdmissionRecord, TeacherProfile, TeacherTeachSubject

TEACHER_TABLES = {
    "teacher_profiles",
    "admission_records",
    "teacher_teach_subjects",
}

FORBIDDEN_COLUMNS = {
    "user_id",
    "phone",
    "mobile",
    "wechat",
    "qq",
    "email",
    "id_card",
    "identity",
    "address",
    "photo",
    "real_name",
    "contact",
    "credential",
    "document_url",
    "is_primary",
}

TEACH_SUBJECT_SCOPE_COPIES = {
    "school_id",
    "subject_code",
    "subject_scope",
}

FORBIDDEN_PROFILE_INDEXES = {
    "ix_teacher_profiles_is_active",
    "ix_teacher_profiles_availability_status",
    "ix_teacher_profiles_verification_status",
}


def _checks(table) -> dict[str, str]:
    return {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def _uniques(table) -> dict[str | None, tuple[str, ...]]:
    return {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _fk_column_sets(table) -> list[tuple[str, ...]]:
    return [
        tuple(fk.column_keys)
        for fk in table.constraints
        if isinstance(fk, ForeignKeyConstraint)
    ]


def _fk_names(table) -> dict[tuple[str, ...], str | None]:
    return {
        tuple(fk.column_keys): fk.name
        for fk in table.constraints
        if isinstance(fk, ForeignKeyConstraint)
    }


def test_teacher_tables_registered_on_metadata() -> None:
    assert TEACHER_TABLES <= set(Base.metadata.tables)


def test_teacher_pk_is_bigint_identity() -> None:
    for table_name in TEACHER_TABLES:
        table = Base.metadata.tables[table_name]
        pk = list(table.primary_key.columns)
        assert len(pk) == 1
        assert pk[0].name == "id"
        assert isinstance(pk[0].type, BigInteger)
        assert pk[0].identity is not None


def test_teacher_profile_columns_types_nullable_defaults() -> None:
    table = TeacherProfile.__table__
    assert isinstance(table.c.display_name.type, String)
    assert table.c.display_name.type.length == 255
    assert table.c.display_name.nullable is False
    assert table.c.display_name.unique is not True
    assert isinstance(table.c.bio.type, Text)
    assert table.c.bio.nullable is True
    assert isinstance(table.c.is_active.type, Boolean)
    assert table.c.is_active.nullable is False
    assert "true" in str(table.c.is_active.server_default.arg).lower()
    assert isinstance(table.c.availability_status.type, String)
    assert table.c.availability_status.nullable is False
    assert "unknown" in str(table.c.availability_status.server_default.arg)
    assert isinstance(table.c.verification_status.type, String)
    assert table.c.verification_status.nullable is False
    assert "unverified" in str(table.c.verification_status.server_default.arg)


def test_teacher_profile_checks() -> None:
    checks = _checks(TeacherProfile.__table__)
    assert "ck_teacher_profiles_availability" in checks
    assert "unknown" in checks["ck_teacher_profiles_availability"]
    assert "available" in checks["ck_teacher_profiles_availability"]
    assert "unavailable" in checks["ck_teacher_profiles_availability"]
    assert "paused" not in checks["ck_teacher_profiles_availability"]
    assert "ck_teacher_profiles_verification" in checks
    assert "unverified" in checks["ck_teacher_profiles_verification"]
    assert "verified" in checks["ck_teacher_profiles_verification"]
    assert "rejected" in checks["ck_teacher_profiles_verification"]
    assert "pending" not in checks["ck_teacher_profiles_verification"]


def test_teacher_profile_has_no_standalone_status_indexes() -> None:
    names = {index.name for index in TeacherProfile.__table__.indexes}
    assert names.isdisjoint(FORBIDDEN_PROFILE_INDEXES)
    assert names == set()


def test_admission_record_score_numeric_and_is_active_default() -> None:
    table = AdmissionRecord.__table__
    for column_name in ("initial_total", "retest_total", "final_total"):
        column = table.c[column_name]
        assert isinstance(column.type, Numeric)
        assert column.type.precision == 8
        assert column.type.scale == 2
        assert column.nullable is True
    assert isinstance(table.c.admission_year.type, SmallInteger)
    assert table.c.admission_catalog_id.nullable is True
    assert table.c.is_active.nullable is False
    assert "true" in str(table.c.is_active.server_default.arg).lower()
    assert "is_primary" not in table.c


def test_admission_record_foreign_keys() -> None:
    names = _fk_names(AdmissionRecord.__table__)
    column_sets = _fk_column_sets(AdmissionRecord.__table__)
    assert names[("teacher_profile_id",)] == "fk_admission_records_teacher_id"
    assert names[("school_id",)] == "fk_admission_records_school_id"
    assert names[("college_id", "school_id")] == "fk_admission_records_college_school"
    assert names[("major_id", "school_id")] == "fk_admission_records_major_school"
    assert names[("admission_catalog_id",)] == "fk_admission_records_catalog_id"
    assert ("college_id",) not in column_sets
    assert ("major_id",) not in column_sets
    # DB deliberately does not enforce Catalog five-tuple equality.
    assert (
        "admission_catalog_id",
        "school_id",
        "college_id",
        "major_id",
        "admission_year",
        "study_mode",
    ) not in column_sets


def test_admission_record_unique_covers_inactive() -> None:
    uniques = _uniques(AdmissionRecord.__table__)
    assert uniques["uq_admission_records_teacher_offering"] == (
        "teacher_profile_id",
        "school_id",
        "college_id",
        "major_id",
        "admission_year",
        "study_mode",
    )
    assert "is_active" not in uniques["uq_admission_records_teacher_offering"]


def test_admission_record_checks() -> None:
    checks = _checks(AdmissionRecord.__table__)
    assert "full_time" in checks["ck_admission_records_study_mode"]
    assert "part_time" in checks["ck_admission_records_study_mode"]
    sql_year = checks["ck_admission_records_year"].lower()
    assert ">= 2000" in sql_year or ">=2000" in sql_year
    assert "2100" not in sql_year
    assert "500" not in checks["ck_admission_records_initial_total_nonnegative"]
    assert "300" not in checks["ck_admission_records_retest_total_nonnegative"]
    assert "100" not in checks["ck_admission_records_final_total_nonnegative"]
    for name in (
        "ck_admission_records_initial_total_nonnegative",
        "ck_admission_records_retest_total_nonnegative",
        "ck_admission_records_final_total_nonnegative",
    ):
        sql = checks[name].lower()
        assert "is null" in sql
        assert ">= 0" in sql or ">=0" in sql


def test_admission_record_indexes() -> None:
    by_name = {
        index.name: tuple(index.columns.keys())
        for index in AdmissionRecord.__table__.indexes
    }
    assert by_name["ix_admission_records_school_year"] == (
        "school_id",
        "admission_year",
    )
    assert by_name["ix_admission_records_college_id"] == ("college_id",)
    assert by_name["ix_admission_records_major_id"] == ("major_id",)
    assert by_name["ix_admission_records_admission_catalog_id"] == (
        "admission_catalog_id",
    )
    assert "ix_admission_records_teacher_profile_id" not in by_name
    assert "ix_admission_records_is_active" not in by_name


def test_teacher_teach_subject_fk_unique_and_subject_index() -> None:
    table = TeacherTeachSubject.__table__
    names = _fk_names(table)
    assert names[("teacher_profile_id",)] == "fk_teacher_teach_subjects_teacher_id"
    assert names[("exam_subject_id",)] == "fk_teacher_teach_subjects_exam_subject_id"
    uniques = _uniques(table)
    assert uniques["uq_teacher_teach_subjects_teacher_subject"] == (
        "teacher_profile_id",
        "exam_subject_id",
    )
    by_name = {
        index.name: tuple(index.columns.keys())
        for index in table.indexes
    }
    assert by_name["ix_teacher_teach_subjects_exam_subject_id"] == (
        "exam_subject_id",
    )
    for columns in by_name.values():
        assert columns != ("teacher_profile_id",)
    assert "is_active" not in table.c
    for copied in TEACH_SUBJECT_SCOPE_COPIES:
        assert copied not in table.c


def test_teacher_models_have_no_orm_relationships() -> None:
    for model in (TeacherProfile, AdmissionRecord, TeacherTeachSubject):
        assert list(inspect(model).relationships) == []


def test_teacher_models_have_no_forbidden_columns() -> None:
    for table_name in TEACHER_TABLES:
        columns = set(Base.metadata.tables[table_name].c.keys())
        assert columns.isdisjoint(FORBIDDEN_COLUMNS)
        assert "verification_status" not in columns or table_name == "teacher_profiles"
