from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class Major(TimestampMixin, Base):
    __tablename__ = "majors"
    __table_args__ = (
        UniqueConstraint("id", "school_id", name="uq_majors_id_school_id"),
        UniqueConstraint("school_id", "major_code", name="uq_majors_school_major_code"),
        CheckConstraint(
            "degree_type IN ('academic', 'professional')",
            name="ck_majors_degree_type",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("schools.id", ondelete="RESTRICT", name="fk_majors_school_id"),
        nullable=False,
    )
    major_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    degree_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
