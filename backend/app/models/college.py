from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Identity,
    Index,
    String,
    UniqueConstraint,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class College(TimestampMixin, Base):
    __tablename__ = "colleges"
    __table_args__ = (
        UniqueConstraint("id", "school_id", name="uq_colleges_id_school_id"),
        Index(
            "uq_colleges_school_college_code",
            "school_id",
            "college_code",
            unique=True,
            postgresql_where=text("college_code IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("schools.id", ondelete="RESTRICT", name="fk_colleges_school_id"),
        nullable=False,
        index=True,
    )
    college_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
