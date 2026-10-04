from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Identity,
    String,
    Text,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class TeacherProfile(TimestampMixin, Base):
    __tablename__ = "teacher_profiles"
    __table_args__ = (
        CheckConstraint(
            "availability_status IN ('unknown', 'available', 'unavailable')",
            name="ck_teacher_profiles_availability",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'rejected')",
            name="ck_teacher_profiles_verification",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )
    availability_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'unknown'"),
    )
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'unverified'"),
    )
