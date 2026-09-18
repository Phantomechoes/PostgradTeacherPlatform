from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.admission_catalog import AdmissionCatalog
    from app.models.exam_subject import ExamSubject


class AdmissionCatalogExamSubject(TimestampMixin, Base):
    __tablename__ = "admission_catalog_exam_subjects"
    __table_args__ = (
        UniqueConstraint(
            "admission_catalog_id",
            "exam_unit",
            "exam_subject_id",
            name="uq_catalog_exam_unit_subject",
        ),
        UniqueConstraint(
            "admission_catalog_id",
            "exam_unit",
            "option_order",
            name="uq_catalog_exam_unit_option_order",
        ),
        CheckConstraint(
            "exam_unit BETWEEN 1 AND 4",
            name="ck_catalog_exam_unit",
        ),
        CheckConstraint(
            "option_order >= 1",
            name="ck_catalog_exam_option_order",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    admission_catalog_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "admission_catalogs.id",
            ondelete="RESTRICT",
            name="fk_admission_catalog_exam_subjects_catalog_id",
        ),
        nullable=False,
    )
    exam_subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "exam_subjects.id",
            ondelete="RESTRICT",
            name="fk_admission_catalog_exam_subjects_subject_id",
        ),
        nullable=False,
        index=True,
    )
    exam_unit: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    option_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    admission_catalog: Mapped[AdmissionCatalog] = relationship(
        back_populates="exam_subjects"
    )
    exam_subject: Mapped[ExamSubject] = relationship(
        back_populates="catalog_exam_subjects"
    )
