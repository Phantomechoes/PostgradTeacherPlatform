from sqlalchemy import BigInteger, ForeignKey, Identity, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base
from app.models.mixins import TimestampMixin


class TeacherTeachSubject(TimestampMixin, Base):
    __tablename__ = "teacher_teach_subjects"
    __table_args__ = (
        UniqueConstraint(
            "teacher_profile_id",
            "exam_subject_id",
            name="uq_teacher_teach_subjects_teacher_subject",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    teacher_profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "teacher_profiles.id",
            ondelete="RESTRICT",
            name="fk_teacher_teach_subjects_teacher_id",
        ),
        nullable=False,
    )
    exam_subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "exam_subjects.id",
            ondelete="RESTRICT",
            name="fk_teacher_teach_subjects_exam_subject_id",
        ),
        nullable=False,
        index=True,
    )
