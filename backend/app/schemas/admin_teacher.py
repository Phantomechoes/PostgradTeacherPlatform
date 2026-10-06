from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.admin_master_data import (
    AdminWriteModel,
    CollegeAdminRead,
    ExamSubjectAdminRead,
    MajorAdminRead,
    SchoolAdminRead,
    StatusUpdate,
    _reject_null,
)
from app.schemas.master_data import Page, StudyMode

AvailabilityStatus = Literal["unknown", "available", "unavailable"]
VerificationStatus = Literal["unverified", "verified", "rejected"]


def _reject_blank(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        raise ValueError("this field cannot be blank")
    return value


class TeacherCreate(AdminWriteModel):
    display_name: str = Field(min_length=1, max_length=255)
    bio: str | None = Field(default=None, min_length=1)

    @field_validator("display_name")
    @classmethod
    def reject_blank_display_name(cls, value: str) -> str:
        return _reject_blank(value)  # type: ignore[return-value]

    @field_validator("bio")
    @classmethod
    def reject_blank_bio(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _reject_blank(value)  # type: ignore[return-value]


class TeacherUpdate(AdminWriteModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = Field(default=None, min_length=1)

    @field_validator("display_name")
    @classmethod
    def reject_null_or_blank_display_name(cls, value: str | None) -> str:
        return _reject_blank(_reject_null(value))  # type: ignore[return-value]

    @field_validator("bio")
    @classmethod
    def reject_blank_bio(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _reject_blank(value)  # type: ignore[return-value]


class AvailabilityUpdate(AdminWriteModel):
    availability_status: AvailabilityStatus


class VerificationUpdate(AdminWriteModel):
    verification_status: VerificationStatus


class AdmissionRecordCreate(AdminWriteModel):
    school_id: int = Field(gt=0)
    college_id: int = Field(gt=0)
    major_id: int = Field(gt=0)
    admission_year: int = Field(ge=2000)
    study_mode: StudyMode
    admission_catalog_id: int | None = Field(default=None, gt=0)
    initial_total: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2
    )
    retest_total: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2
    )
    final_total: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2
    )


class AdmissionRecordUpdate(AdminWriteModel):
    school_id: int | None = Field(default=None, gt=0)
    college_id: int | None = Field(default=None, gt=0)
    major_id: int | None = Field(default=None, gt=0)
    admission_year: int | None = Field(default=None, ge=2000)
    study_mode: StudyMode | None = None
    admission_catalog_id: int | None = Field(default=None, gt=0)
    initial_total: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2
    )
    retest_total: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2
    )
    final_total: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2
    )

    @field_validator(
        "school_id",
        "college_id",
        "major_id",
        "admission_year",
        "study_mode",
    )
    @classmethod
    def reject_null_identity(cls, value: object) -> object:
        return _reject_null(value)


class TeachSubjectsPut(AdminWriteModel):
    exam_subject_ids: list[int]

    @field_validator("exam_subject_ids")
    @classmethod
    def unique_positive_ids(cls, ids: list[int]) -> list[int]:
        if any(item <= 0 for item in ids):
            raise ValueError("exam_subject_id must be greater than 0")
        if len(ids) != len(set(ids)):
            raise ValueError("exam_subject_ids must not contain duplicates")
        return ids


class AdmissionRecordAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_profile_id: int
    school: SchoolAdminRead
    college: CollegeAdminRead
    major: MajorAdminRead
    admission_year: int
    study_mode: StudyMode
    admission_catalog_id: int | None
    initial_total: Decimal | None
    retest_total: Decimal | None
    final_total: Decimal | None
    is_active: bool

    @field_serializer("initial_total", "retest_total", "final_total", when_used="json")
    def serialize_score(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)


class TeacherAdminSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    bio: str | None
    is_active: bool
    availability_status: AvailabilityStatus
    verification_status: VerificationStatus


class TeacherAdminDetail(TeacherAdminSummary):
    admission_records: list[AdmissionRecordAdminRead]
    teach_subjects: list[ExamSubjectAdminRead]


__all__ = [
    "AdmissionRecordAdminRead",
    "AdmissionRecordCreate",
    "AdmissionRecordUpdate",
    "AvailabilityStatus",
    "AvailabilityUpdate",
    "Page",
    "StatusUpdate",
    "TeachSubjectsPut",
    "TeacherAdminDetail",
    "TeacherAdminSummary",
    "TeacherCreate",
    "TeacherUpdate",
    "VerificationStatus",
    "VerificationUpdate",
]
