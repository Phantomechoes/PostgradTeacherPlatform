from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Identity, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.admission_catalog import AdmissionCatalog
    from app.models.college import College
    from app.models.exam_subject import ExamSubject
    from app.models.major import Major


class School(TimestampMixin, Base):
    __tablename__ = "schools"
    __table_args__ = (
        UniqueConstraint("school_code", name="uq_schools_school_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    school_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )

    colleges: Mapped[list[College]] = relationship(back_populates="school")
    majors: Mapped[list[Major]] = relationship(back_populates="school")
    exam_subjects: Mapped[list[ExamSubject]] = relationship(back_populates="school")
    admission_catalogs: Mapped[list[AdmissionCatalog]] = relationship(
        back_populates="school"
    )
