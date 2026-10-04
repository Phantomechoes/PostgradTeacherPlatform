from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class AdmissionRecord(TimestampMixin, Base):
    __tablename__ = "admission_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["college_id", "school_id"],
            ["colleges.id", "colleges.school_id"],
            name="fk_admission_records_college_school",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["major_id", "school_id"],
            ["majors.id", "majors.school_id"],
            name="fk_admission_records_major_school",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "teacher_profile_id",
            "school_id",
            "college_id",
            "major_id",
            "admission_year",
            "study_mode",
            name="uq_admission_records_teacher_offering",
        ),
        CheckConstraint(
            "study_mode IN ('full_time', 'part_time')",
            name="ck_admission_records_study_mode",
        ),
        CheckConstraint(
            "admission_year >= 2000",
            name="ck_admission_records_year",
        ),
        CheckConstraint(
            "initial_total IS NULL OR initial_total >= 0",
            name="ck_admission_records_initial_total_nonnegative",
        ),
        CheckConstraint(
            "retest_total IS NULL OR retest_total >= 0",
            name="ck_admission_records_retest_total_nonnegative",
        ),
        CheckConstraint(
            "final_total IS NULL OR final_total >= 0",
            name="ck_admission_records_final_total_nonnegative",
        ),
        Index("ix_admission_records_school_year", "school_id", "admission_year"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    teacher_profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "teacher_profiles.id",
            ondelete="RESTRICT",
            name="fk_admission_records_teacher_id",
        ),
        nullable=False,
    )
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "schools.id",
            ondelete="RESTRICT",
            name="fk_admission_records_school_id",
        ),
        nullable=False,
    )
    college_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    major_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    admission_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    study_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    admission_catalog_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "admission_catalogs.id",
            ondelete="RESTRICT",
            name="fk_admission_records_catalog_id",
        ),
        nullable=True,
        index=True,
    )
    initial_total: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    retest_total: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    final_total: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
