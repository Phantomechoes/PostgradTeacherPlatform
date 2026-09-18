from __future__ import annotations

from typing import TYPE_CHECKING

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.admission_catalog_direction import AdmissionCatalogDirection
    from app.models.admission_catalog_exam_subject import AdmissionCatalogExamSubject
    from app.models.college import College
    from app.models.major import Major
    from app.models.school import School


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
        ForeignKey("schools.id", ondelete="RESTRICT", name="fk_admission_catalogs_school_id"),
        nullable=False,
    )
    college_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    major_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    admission_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    study_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )

    school: Mapped[School] = relationship(back_populates="admission_catalogs")
    college: Mapped[College] = relationship(back_populates="admission_catalogs")
    major: Mapped[Major] = relationship(back_populates="admission_catalogs")
    directions: Mapped[list[AdmissionCatalogDirection]] = relationship(
        back_populates="admission_catalog"
    )
    exam_subjects: Mapped[list[AdmissionCatalogExamSubject]] = relationship(
        back_populates="admission_catalog"
    )
