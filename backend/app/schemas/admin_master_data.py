from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.master_data import DegreeType, Page

AdminStatus = Literal["all", "active", "inactive"]


class AdminWriteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _reject_null(value: object) -> object:
    if value is None:
        raise ValueError("this field cannot be null")
    return value


class StatusUpdate(AdminWriteModel):
    is_active: bool


class SchoolCreate(AdminWriteModel):
    school_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)


class SchoolUpdate(AdminWriteModel):
    school_code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("school_code", "name")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        return _reject_null(value)  # type: ignore[return-value]


class SchoolAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_code: str
    name: str
    is_active: bool


class CollegeCreate(AdminWriteModel):
    college_code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)


class CollegeUpdate(AdminWriteModel):
    college_code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: str | None) -> str:
        return _reject_null(value)  # type: ignore[return-value]


class CollegeAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    college_code: str | None
    name: str
    is_active: bool


class MajorCreate(AdminWriteModel):
    major_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    degree_type: DegreeType


class MajorUpdate(AdminWriteModel):
    major_code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    degree_type: DegreeType | None = None

    @field_validator("major_code", "name", "degree_type")
    @classmethod
    def reject_null(cls, value: object) -> object:
        return _reject_null(value)


class MajorAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    major_code: str
    name: str
    degree_type: DegreeType
    is_active: bool


class ExamSubjectCreate(AdminWriteModel):
    subject_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)


class ExamSubjectUpdate(AdminWriteModel):
    subject_code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("subject_code", "name")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        return _reject_null(value)  # type: ignore[return-value]


class ExamSubjectAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int | None
    subject_code: str
    name: str
    is_active: bool


__all__ = [
    "AdminStatus",
    "CollegeAdminRead",
    "CollegeCreate",
    "CollegeUpdate",
    "ExamSubjectAdminRead",
    "ExamSubjectCreate",
    "ExamSubjectUpdate",
    "MajorAdminRead",
    "MajorCreate",
    "MajorUpdate",
    "Page",
    "SchoolAdminRead",
    "SchoolCreate",
    "SchoolUpdate",
    "StatusUpdate",
]
