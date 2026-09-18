from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Identity,
    Index,
    String,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class ExamSubject(TimestampMixin, Base):
    __tablename__ = "exam_subjects"
    __table_args__ = (
        Index(
            "uq_exam_subjects_national_code",
            "subject_code",
            unique=True,
            postgresql_where=text("school_id IS NULL"),
        ),
        Index(
            "uq_exam_subjects_school_code",
            "school_id",
            "subject_code",
            unique=True,
            postgresql_where=text("school_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    school_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("schools.id", ondelete="RESTRICT", name="fk_exam_subjects_school_id"),
        nullable=True,
        index=True,
    )
    subject_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
