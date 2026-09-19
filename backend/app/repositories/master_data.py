from dataclasses import dataclass

from sqlalchemy import Select, func, nulls_last, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AdmissionCatalog,
    AdmissionCatalogDirection,
    AdmissionCatalogExamSubject,
    College,
    ExamSubject,
    Major,
    School,
)


@dataclass(frozen=True, slots=True)
class CatalogRow:
    catalog: AdmissionCatalog
    school: School
    college: College
    major: Major


@dataclass(frozen=True, slots=True)
class CatalogExamOptionRow:
    link: AdmissionCatalogExamSubject
    subject: ExamSubject


def _college_same_school():
    return (AdmissionCatalog.college_id == College.id) & (
        AdmissionCatalog.school_id == College.school_id
    )


def _major_same_school():
    return (AdmissionCatalog.major_id == Major.id) & (
        AdmissionCatalog.school_id == Major.school_id
    )


class SchoolRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_active_by_id(self, school_id: int) -> School | None:
        return self._session.scalar(
            select(School).where(
                School.id == school_id,
                School.is_active.is_(True),
            )
        )

    def list_schools(
        self,
        *,
        q: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[School], int]:
        stmt = select(School).where(School.is_active.is_(True))
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

    def list_colleges(self, school_id: int) -> list[College]:
        stmt = (
            select(College)
            .where(
                College.school_id == school_id,
                College.is_active.is_(True),
            )
            .order_by(
                nulls_last(College.college_code.asc()),
                College.name.asc(),
                College.id.asc(),
            )
        )
        return list(self._session.scalars(stmt).all())

    def list_majors(self, school_id: int) -> list[Major]:
        stmt = (
            select(Major)
            .where(
                Major.school_id == school_id,
                Major.is_active.is_(True),
            )
            .order_by(Major.major_code.asc(), Major.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_admission_years(self, school_id: int) -> list[int]:
        stmt = (
            select(AdmissionCatalog.admission_year)
            .join(College, _college_same_school())
            .join(Major, _major_same_school())
            .where(
                AdmissionCatalog.school_id == school_id,
                AdmissionCatalog.is_active.is_(True),
                College.is_active.is_(True),
                Major.is_active.is_(True),
            )
            .distinct()
            .order_by(AdmissionCatalog.admission_year.desc())
        )
        return list(self._session.scalars(stmt).all())


class AdmissionCatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_catalogs(
        self,
        *,
        school_id: int,
        admission_year: int | None,
        college_id: int | None,
        major_id: int | None,
        study_mode: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[CatalogRow], int]:
        filtered = self._filter_catalogs(
            self._visible_catalogs(select(AdmissionCatalog, School, College, Major)),
            school_id=school_id,
            admission_year=admission_year,
            college_id=college_id,
            major_id=major_id,
            study_mode=study_mode,
        )
        total = self._session.scalar(
            select(func.count()).select_from(
                self._filter_catalogs(
                    self._visible_catalogs(select(AdmissionCatalog.id)),
                    school_id=school_id,
                    admission_year=admission_year,
                    college_id=college_id,
                    major_id=major_id,
                    study_mode=study_mode,
                ).subquery()
            )
        )
        rows = self._session.execute(
            filtered.order_by(
                AdmissionCatalog.admission_year.desc(),
                AdmissionCatalog.college_id.asc(),
                AdmissionCatalog.major_id.asc(),
                AdmissionCatalog.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        ).all()
        return (
            [
                CatalogRow(catalog=catalog, school=school, college=college, major=major)
                for catalog, school, college, major in rows
            ],
            int(total or 0),
        )

    def get_catalog(self, catalog_id: int) -> CatalogRow | None:
        row = self._session.execute(
            self._visible_catalogs(
                select(AdmissionCatalog, School, College, Major)
            ).where(AdmissionCatalog.id == catalog_id)
        ).one_or_none()
        if row is None:
            return None
        catalog, school, college, major = row
        return CatalogRow(
            catalog=catalog, school=school, college=college, major=major
        )

    def list_directions(self, catalog_id: int) -> list[AdmissionCatalogDirection]:
        stmt = (
            select(AdmissionCatalogDirection)
            .where(AdmissionCatalogDirection.admission_catalog_id == catalog_id)
            .order_by(
                AdmissionCatalogDirection.direction_code.asc(),
                AdmissionCatalogDirection.id.asc(),
            )
        )
        return list(self._session.scalars(stmt).all())

    def list_exam_options(self, catalog_id: int) -> list[CatalogExamOptionRow]:
        stmt = (
            select(AdmissionCatalogExamSubject, ExamSubject)
            .join(
                ExamSubject,
                AdmissionCatalogExamSubject.exam_subject_id == ExamSubject.id,
            )
            .where(
                AdmissionCatalogExamSubject.admission_catalog_id == catalog_id,
                ExamSubject.is_active.is_(True),
            )
            .order_by(
                AdmissionCatalogExamSubject.exam_unit.asc(),
                AdmissionCatalogExamSubject.option_order.asc(),
                AdmissionCatalogExamSubject.id.asc(),
            )
        )
        return [
            CatalogExamOptionRow(link=link, subject=subject)
            for link, subject in self._session.execute(stmt).all()
        ]

    def _visible_catalogs(self, stmt: Select) -> Select:
        return (
            stmt.join(School, AdmissionCatalog.school_id == School.id)
            .join(College, _college_same_school())
            .join(Major, _major_same_school())
            .where(
                AdmissionCatalog.is_active.is_(True),
                School.is_active.is_(True),
                College.is_active.is_(True),
                Major.is_active.is_(True),
            )
        )

    def _filter_catalogs(
        self,
        stmt: Select,
        *,
        school_id: int,
        admission_year: int | None,
        college_id: int | None,
        major_id: int | None,
        study_mode: str | None,
    ) -> Select:
        stmt = stmt.where(AdmissionCatalog.school_id == school_id)
        if admission_year is not None:
            stmt = stmt.where(AdmissionCatalog.admission_year == admission_year)
        if college_id is not None:
            stmt = stmt.where(AdmissionCatalog.college_id == college_id)
        if major_id is not None:
            stmt = stmt.where(AdmissionCatalog.major_id == major_id)
        if study_mode is not None:
            stmt = stmt.where(AdmissionCatalog.study_mode == study_mode)
        return stmt
