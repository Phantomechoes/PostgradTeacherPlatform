from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class AdmissionCatalog(TimestampMixin, Base):
    __tablename__ = "admission_catalogs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["college_id", "school_id"],
            ["colleges.id", "colleges.school_id"],
            name="fk_admission_catalogs_college_school",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["major_id", "school_id"],
            ["majors.id", "majors.school_id"],
            name="fk_admission_catalogs_major_school",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "school_id",
            "college_id",
            "major_id",
            "admission_year",
            "study_mode",
            name="uq_admission_catalogs_offering",
        ),
        CheckConstraint(
            "study_mode IN ('full_time', 'part_time')",
            name="ck_admission_catalogs_study_mode",
        ),
        CheckConstraint(
            "admission_year >= 2000",
            name="ck_admission_catalogs_year",
        ),
        Index("ix_admission_catalogs_year", "admission_year"),
        Index("ix_admission_catalogs_school_year", "school_id", "admission_year"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "schools.id", ondelete="RESTRICT", name="fk_admission_catalogs_school_id"
        ),
        nullable=False,
    )
    college_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    major_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    admission_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    study_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
