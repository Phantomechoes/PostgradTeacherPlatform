from sqlalchemy import BigInteger, ForeignKey, Identity, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class AdmissionCatalogDirection(TimestampMixin, Base):
    __tablename__ = "admission_catalog_directions"
    __table_args__ = (
        UniqueConstraint(
            "admission_catalog_id",
            "direction_code",
            name="uq_admission_catalog_directions_code",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    admission_catalog_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "admission_catalogs.id",
            ondelete="RESTRICT",
            name="fk_admission_catalog_directions_catalog_id",
        ),
        nullable=False,
    )
    direction_code: Mapped[str] = mapped_column(String(32), nullable=False)
    direction_name: Mapped[str] = mapped_column(String(255), nullable=False)
