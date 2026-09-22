from dataclasses import dataclass

from sqlalchemy import Select, delete, func, select
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
from app.repositories.admin_master_data import _apply_status
from app.schemas.admin_master_data import AdminStatus


@dataclass(frozen=True, slots=True)
class AdminCatalogRow:
    catalog: AdmissionCatalog
    school: School
    college: College
    major: Major


@dataclass(frozen=True, slots=True)
class AdminExamOptionRow:
    link: AdmissionCatalogExamSubject
    subject: ExamSubject


def _same_school_college():
    return (AdmissionCatalog.college_id == College.id) & (
        AdmissionCatalog.school_id == College.school_id
    )


def _same_school_major():
    return (AdmissionCatalog.major_id == Major.id) & (
        AdmissionCatalog.school_id == Major.school_id
    )


class AdminCatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_catalog(self, catalog_id: int) -> AdmissionCatalog | None:
        return self._session.get(AdmissionCatalog, catalog_id)

    def get_catalog_row(self, catalog_id: int) -> AdminCatalogRow | None:
        row = self._session.execute(
            self._joined(select(AdmissionCatalog, School, College, Major)).where(
                AdmissionCatalog.id == catalog_id
            )
        ).one_or_none()
        if row is None:
            return None
        catalog, school, college, major = row
        return AdminCatalogRow(
            catalog=catalog, school=school, college=college, major=major
        )

    def list_catalogs(
        self,
        *,
        school_id: int,
        status: AdminStatus,
        admission_year: int | None,
        college_id: int | None,
        major_id: int | None,
        study_mode: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[AdminCatalogRow], int]:
        filtered = self._filter(
            self._joined(select(AdmissionCatalog, School, College, Major)),
            school_id=school_id,
            status=status,
            admission_year=admission_year,
            college_id=college_id,
            major_id=major_id,
            study_mode=study_mode,
        )
        total = self._session.scalar(
            select(func.count()).select_from(
                self._filter(
                    self._joined(select(AdmissionCatalog.id)),
                    school_id=school_id,
                    status=status,
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
                AdminCatalogRow(
                    catalog=catalog, school=school, college=college, major=major
                )
                for catalog, school, college, major in rows
            ],
            int(total or 0),
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

    def list_exam_options(self, catalog_id: int) -> list[AdminExamOptionRow]:
        stmt = (
            select(AdmissionCatalogExamSubject, ExamSubject)
            .join(
                ExamSubject,
                AdmissionCatalogExamSubject.exam_subject_id == ExamSubject.id,
            )
            .where(AdmissionCatalogExamSubject.admission_catalog_id == catalog_id)
            .order_by(
                AdmissionCatalogExamSubject.exam_unit.asc(),
                AdmissionCatalogExamSubject.option_order.asc(),
                AdmissionCatalogExamSubject.id.asc(),
            )
        )
        return [
            AdminExamOptionRow(link=link, subject=subject)
            for link, subject in self._session.execute(stmt).all()
        ]

    def add(self, entity: object) -> None:
        self._session.add(entity)

    def delete_directions(self, catalog_id: int) -> None:
        self._session.execute(
            delete(AdmissionCatalogDirection).where(
                AdmissionCatalogDirection.admission_catalog_id == catalog_id
            )
        )

    def delete_exam_options(self, catalog_id: int) -> None:
        self._session.execute(
            delete(AdmissionCatalogExamSubject).where(
                AdmissionCatalogExamSubject.admission_catalog_id == catalog_id
            )
        )

    def flush(self) -> None:
        self._session.flush()

    def _joined(self, stmt: Select) -> Select:
        return (
            stmt.join(School, AdmissionCatalog.school_id == School.id)
            .join(College, _same_school_college())
            .join(Major, _same_school_major())
        )

    def _filter(
        self,
        stmt: Select,
        *,
        school_id: int,
        status: AdminStatus,
        admission_year: int | None,
        college_id: int | None,
        major_id: int | None,
        study_mode: str | None,
    ) -> Select:
        stmt = _apply_status(stmt, AdmissionCatalog.is_active, status)
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
