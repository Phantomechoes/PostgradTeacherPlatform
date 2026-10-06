from dataclasses import dataclass

from sqlalchemy import Select, delete, exists, func, select
from sqlalchemy.orm import Session

from app.models import (
    AdmissionRecord,
    College,
    ExamSubject,
    Major,
    School,
    TeacherProfile,
    TeacherTeachSubject,
)
from app.repositories.admin_master_data import _apply_status
from app.schemas.admin_master_data import AdminStatus
from app.schemas.admin_teacher import AvailabilityStatus, VerificationStatus


@dataclass(frozen=True, slots=True)
class AdminAdmissionRow:
    admission: AdmissionRecord
    school: School
    college: College
    major: Major


@dataclass(frozen=True, slots=True)
class AdminTeachSubjectRow:
    link: TeacherTeachSubject
    subject: ExamSubject


def _same_school_college():
    return (AdmissionRecord.college_id == College.id) & (
        AdmissionRecord.school_id == College.school_id
    )


def _same_school_major():
    return (AdmissionRecord.major_id == Major.id) & (
        AdmissionRecord.school_id == Major.school_id
    )


class AdminTeacherRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_teacher(self, teacher_profile_id: int) -> TeacherProfile | None:
        return self._session.get(TeacherProfile, teacher_profile_id)

    def add_teacher(self, teacher: TeacherProfile) -> None:
        self._session.add(teacher)

    def list_teachers(
        self,
        *,
        status: AdminStatus,
        availability: AvailabilityStatus | None,
        verification: VerificationStatus | None,
        q: str | None,
        school_id: int | None,
        college_id: int | None,
        major_id: int | None,
        admission_year: int | None,
        study_mode: str | None,
        exam_subject_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[TeacherProfile], int]:
        stmt = _apply_status(select(TeacherProfile), TeacherProfile.is_active, status)
        if availability is not None:
            stmt = stmt.where(TeacherProfile.availability_status == availability)
        if verification is not None:
            stmt = stmt.where(TeacherProfile.verification_status == verification)
        if q is not None:
            stmt = stmt.where(TeacherProfile.display_name.ilike(f"%{q}%"))
        stmt = self._apply_admission_exists(
            stmt,
            school_id=school_id,
            college_id=college_id,
            major_id=major_id,
            admission_year=admission_year,
            study_mode=study_mode,
        )
        if exam_subject_id is not None:
            stmt = stmt.where(
                exists().where(
                    TeacherTeachSubject.teacher_profile_id == TeacherProfile.id,
                    TeacherTeachSubject.exam_subject_id == exam_subject_id,
                )
            )
        total = self._session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        items = list(
            self._session.scalars(
                stmt.order_by(TeacherProfile.display_name.asc(), TeacherProfile.id.asc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, int(total or 0)

    def get_admission(self, admission_record_id: int) -> AdmissionRecord | None:
        return self._session.get(AdmissionRecord, admission_record_id)

    def add_admission(self, admission: AdmissionRecord) -> None:
        self._session.add(admission)

    def get_admission_row(self, admission_record_id: int) -> AdminAdmissionRow | None:
        row = self._session.execute(
            self._joined_admissions(
                select(AdmissionRecord, School, College, Major)
            ).where(AdmissionRecord.id == admission_record_id)
        ).one_or_none()
        if row is None:
            return None
        admission, school, college, major = row
        return AdminAdmissionRow(
            admission=admission,
            school=school,
            college=college,
            major=major,
        )

    def list_admissions_for_teacher(
        self,
        teacher_profile_id: int,
    ) -> list[AdminAdmissionRow]:
        stmt = (
            self._joined_admissions(select(AdmissionRecord, School, College, Major))
            .where(AdmissionRecord.teacher_profile_id == teacher_profile_id)
            .order_by(
                AdmissionRecord.is_active.desc(),
                AdmissionRecord.admission_year.desc(),
                AdmissionRecord.id.asc(),
            )
        )
        return [
            AdminAdmissionRow(
                admission=admission,
                school=school,
                college=college,
                major=major,
            )
            for admission, school, college, major in self._session.execute(stmt).all()
        ]

    def list_teach_subjects_for_teacher(
        self,
        teacher_profile_id: int,
    ) -> list[AdminTeachSubjectRow]:
        stmt = (
            select(TeacherTeachSubject, ExamSubject)
            .join(
                ExamSubject,
                TeacherTeachSubject.exam_subject_id == ExamSubject.id,
            )
            .where(TeacherTeachSubject.teacher_profile_id == teacher_profile_id)
            .order_by(TeacherTeachSubject.exam_subject_id.asc())
        )
        return [
            AdminTeachSubjectRow(link=link, subject=subject)
            for link, subject in self._session.execute(stmt).all()
        ]

    def delete_teach_subjects_for_teacher(self, teacher_profile_id: int) -> None:
        self._session.execute(
            delete(TeacherTeachSubject).where(
                TeacherTeachSubject.teacher_profile_id == teacher_profile_id
            )
        )

    def add_teach_subject(self, link: TeacherTeachSubject) -> None:
        self._session.add(link)

    def flush(self) -> None:
        self._session.flush()

    def _joined_admissions(self, stmt: Select) -> Select:
        return (
            stmt.join(School, AdmissionRecord.school_id == School.id)
            .join(College, _same_school_college())
            .join(Major, _same_school_major())
        )

    def _apply_admission_exists(
        self,
        stmt: Select,
        *,
        school_id: int | None,
        college_id: int | None,
        major_id: int | None,
        admission_year: int | None,
        study_mode: str | None,
    ) -> Select:
        filters = (
            school_id,
            college_id,
            major_id,
            admission_year,
            study_mode,
        )
        if all(value is None for value in filters):
            return stmt
        conditions = [
            AdmissionRecord.teacher_profile_id == TeacherProfile.id,
            AdmissionRecord.is_active.is_(True),
        ]
        if school_id is not None:
            conditions.append(AdmissionRecord.school_id == school_id)
        if college_id is not None:
            conditions.append(AdmissionRecord.college_id == college_id)
        if major_id is not None:
            conditions.append(AdmissionRecord.major_id == major_id)
        if admission_year is not None:
            conditions.append(AdmissionRecord.admission_year == admission_year)
        if study_mode is not None:
            conditions.append(AdmissionRecord.study_mode == study_mode)
        return stmt.where(exists().where(*conditions))
