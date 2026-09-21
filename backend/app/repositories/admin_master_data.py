from sqlalchemy import Select, func, nulls_last, or_, select
from sqlalchemy.orm import Session

from app.models import College, ExamSubject, Major, School
from app.schemas.admin_master_data import AdminStatus


def _apply_status[T](stmt: Select[T], column, status: AdminStatus) -> Select[T]:
    if status == "active":
        return stmt.where(column.is_(True))
    if status == "inactive":
        return stmt.where(column.is_(False))
    return stmt


class AdminSchoolRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_school(self, school_id: int) -> School | None:
        return self._session.get(School, school_id)

    def get_college(self, college_id: int) -> College | None:
        return self._session.get(College, college_id)

    def get_major(self, major_id: int) -> Major | None:
        return self._session.get(Major, major_id)

    def get_exam_subject(self, exam_subject_id: int) -> ExamSubject | None:
        return self._session.get(ExamSubject, exam_subject_id)

    def list_schools(
        self,
        *,
        status: AdminStatus,
        q: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[School], int]:
        stmt = _apply_status(select(School), School.is_active, status)
        if q is not None:
            pattern = f"%{q}%"
            stmt = stmt.where(
                or_(
                    School.school_code.ilike(pattern),
                    School.name.ilike(pattern),
                )
            )
        total = self._session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        items = list(
            self._session.scalars(
                stmt.order_by(School.school_code.asc(), School.id.asc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, int(total or 0)

    def list_colleges(
        self,
        *,
        school_id: int,
        status: AdminStatus,
    ) -> list[College]:
        stmt = _apply_status(
            select(College).where(College.school_id == school_id),
            College.is_active,
            status,
        )
        return list(
            self._session.scalars(
                stmt.order_by(
                    nulls_last(College.college_code.asc()),
                    College.name.asc(),
                    College.id.asc(),
                )
            ).all()
        )

    def list_majors(
        self,
        *,
        school_id: int,
        status: AdminStatus,
    ) -> list[Major]:
        stmt = _apply_status(
            select(Major).where(Major.school_id == school_id),
            Major.is_active,
            status,
        )
        return list(
            self._session.scalars(
                stmt.order_by(Major.major_code.asc(), Major.id.asc())
            ).all()
        )

    def list_national_exam_subjects(
        self,
        *,
        status: AdminStatus,
    ) -> list[ExamSubject]:
        stmt = _apply_status(
            select(ExamSubject).where(ExamSubject.school_id.is_(None)),
            ExamSubject.is_active,
            status,
        )
        return list(
            self._session.scalars(
                stmt.order_by(ExamSubject.subject_code.asc(), ExamSubject.id.asc())
            ).all()
        )

    def list_school_exam_subjects(
        self,
        *,
        school_id: int,
        status: AdminStatus,
    ) -> list[ExamSubject]:
        stmt = _apply_status(
            select(ExamSubject).where(ExamSubject.school_id == school_id),
            ExamSubject.is_active,
            status,
        )
        return list(
            self._session.scalars(
                stmt.order_by(ExamSubject.subject_code.asc(), ExamSubject.id.asc())
            ).all()
        )

    def add(self, entity: School | College | Major | ExamSubject) -> None:
        self._session.add(entity)

    def flush(self) -> None:
        self._session.flush()
