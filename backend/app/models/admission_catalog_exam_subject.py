from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


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
