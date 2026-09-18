from sqlalchemy import BigInteger, Boolean, Identity, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


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
