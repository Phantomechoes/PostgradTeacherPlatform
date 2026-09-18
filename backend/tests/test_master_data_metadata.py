import ast
from pathlib import Path

from sqlalchemy import BigInteger, CheckConstraint, SmallInteger, String, inspect
from sqlalchemy.sql.schema import ForeignKeyConstraint, UniqueConstraint

from app.core.db_base import Base
from app.models import (
    AdmissionCatalog,
    AdmissionCatalogDirection,
    AdmissionCatalogExamSubject,
    College,
    ExamSubject,
    Major,
    School,
)

MODELS_DIR = Path(__file__).resolve().parents[1] / "app" / "models"

EXPECTED_TABLES = {
    "schools",
    "colleges",
    "majors",
    "admission_catalogs",
    "admission_catalog_directions",
    "exam_subjects",
    "admission_catalog_exam_subjects",
}

CODE_COLUMNS = {
    "schools": ("school_code",),
    "colleges": ("college_code",),
    "majors": ("major_code",),
    "exam_subjects": ("subject_code",),
    "admission_catalog_directions": ("direction_code",),
}


def test_import_app_models_registers_all_tables() -> None:
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_models_do_not_import_database_module() -> None:
    for path in MODELS_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module != "app.core.database", path.name
                assert not node.module.startswith("app.core.database")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "app.core.database"


def test_pk_is_bigint_identity() -> None:
    for table in Base.metadata.tables.values():
        if table.name not in EXPECTED_TABLES:
            continue
        pk = list(table.primary_key.columns)
        assert len(pk) == 1
        assert pk[0].name == "id"
        assert isinstance(pk[0].type, BigInteger)
        assert pk[0].identity is not None


def test_code_columns_are_string_not_integer() -> None:
    for table_name, columns in CODE_COLUMNS.items():
        table = Base.metadata.tables[table_name]
        for col in columns:
            assert isinstance(table.c[col].type, String), f"{table_name}.{col}"


def test_school_code_unique_named() -> None:
    named = {
        u.name: tuple(c.name for c in u.columns)
        for u in School.__table__.constraints
        if isinstance(u, UniqueConstraint)
    }
    assert named.get("uq_schools_school_code") == ("school_code",)
    assert School.__table__.c.school_code.unique is not True


def test_admission_year_check_has_no_upper_bound() -> None:
    checks = [
        c
        for c in AdmissionCatalog.__table__.constraints
        if isinstance(c, CheckConstraint) and c.name == "ck_admission_catalogs_year"
    ]
    assert len(checks) == 1
    sql = str(checks[0].sqltext).lower()
    assert ">= 2000" in sql or ">=2000" in sql
    assert "2100" not in sql
    assert "between" not in sql


def test_single_column_foreign_keys_are_named() -> None:
    expected = {
        ("colleges", "school_id"): "fk_colleges_school_id",
        ("majors", "school_id"): "fk_majors_school_id",
        ("exam_subjects", "school_id"): "fk_exam_subjects_school_id",
        ("admission_catalogs", "school_id"): "fk_admission_catalogs_school_id",
        ("admission_catalog_directions", "admission_catalog_id"): (
            "fk_admission_catalog_directions_catalog_id"
        ),
        ("admission_catalog_exam_subjects", "admission_catalog_id"): (
            "fk_admission_catalog_exam_subjects_catalog_id"
        ),
        ("admission_catalog_exam_subjects", "exam_subject_id"): (
            "fk_admission_catalog_exam_subjects_subject_id"
        ),
    }
    for (table_name, column_name), fk_name in expected.items():
        table = Base.metadata.tables[table_name]
        fks = [
            fk
            for fk in table.constraints
            if isinstance(fk, ForeignKeyConstraint) and list(fk.column_keys) == [column_name]
        ]
        assert len(fks) == 1, table_name
        assert fks[0].name == fk_name


def test_redundant_indexes_removed() -> None:
    all_index_names = {
        idx.name for table in Base.metadata.tables.values() for idx in table.indexes
    }
    assert "ix_majors_school_id" not in all_index_names
    assert "ix_admission_catalog_directions_admission_catalog_id" not in all_index_names
    assert "ix_admission_catalog_exam_subjects_admission_catalog_id" not in all_index_names


def test_small_integer_columns() -> None:
    assert isinstance(AdmissionCatalog.__table__.c.admission_year.type, SmallInteger)
    exam = AdmissionCatalogExamSubject.__table__
    assert isinstance(exam.c.exam_unit.type, SmallInteger)
    assert isinstance(exam.c.option_order.type, SmallInteger)


def test_catalog_composite_foreign_keys() -> None:
    fks = [
        fk
        for fk in AdmissionCatalog.__table__.constraints
        if isinstance(fk, ForeignKeyConstraint)
    ]
    referred = {tuple(fk.elements[0].target_fullname.split(".")[0] for _ in [0]) for fk in fks}
    column_sets = [tuple(fk.column_keys) for fk in fks]
    assert ("college_id", "school_id") in column_sets
    assert ("major_id", "school_id") in column_sets
    assert referred or fks


def test_exam_subject_partial_unique_indexes() -> None:
    names = {idx.name for idx in ExamSubject.__table__.indexes}
    assert "uq_exam_subjects_national_code" in names
    assert "uq_exam_subjects_school_code" in names
    by_name = {idx.name: idx for idx in ExamSubject.__table__.indexes}
    assert by_name["uq_exam_subjects_national_code"].unique is True
    assert by_name["uq_exam_subjects_school_code"].unique is True
    assert by_name["uq_exam_subjects_national_code"].dialect_options["postgresql"]["where"] is not None
    assert by_name["uq_exam_subjects_school_code"].dialect_options["postgresql"]["where"] is not None


def test_catalog_exam_subject_checks_and_uniques() -> None:
    checks = {
        c.name
        for c in AdmissionCatalogExamSubject.__table__.constraints
        if isinstance(c, CheckConstraint)
    }
    uniques = {
        tuple(col.name for col in u.columns)
        for u in AdmissionCatalogExamSubject.__table__.constraints
        if isinstance(u, UniqueConstraint)
    }
    assert "ck_catalog_exam_unit" in checks
    assert "ck_catalog_exam_option_order" in checks
    assert ("admission_catalog_id", "exam_unit", "exam_subject_id") in uniques
    assert ("admission_catalog_id", "exam_unit", "option_order") in uniques


def test_no_research_direction_on_catalog() -> None:
    columns = set(AdmissionCatalog.__table__.c.keys())
    assert "research_direction_code" not in columns
    assert "research_direction_name" not in columns


def test_major_has_no_college_id() -> None:
    assert "college_id" not in Major.__table__.c


def test_direction_has_no_exam_subject_fk() -> None:
    assert "exam_subject_id" not in AdmissionCatalogDirection.__table__.c


def test_mapper_configuration() -> None:
    inspect(School)
    inspect(College)
    inspect(Major)
    inspect(AdmissionCatalog)
    inspect(AdmissionCatalogDirection)
    inspect(ExamSubject)
    inspect(AdmissionCatalogExamSubject)
