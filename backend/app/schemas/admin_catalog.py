from pydantic import Field, field_validator, model_validator

from app.schemas.admin_master_data import (
    AdminWriteModel,
    CollegeAdminRead,
    ExamSubjectAdminRead,
    MajorAdminRead,
    SchoolAdminRead,
    _reject_null,
)
from app.schemas.master_data import Page, StudyMode


class DirectionWrite(AdminWriteModel):
    direction_code: str = Field(min_length=1, max_length=32)
    direction_name: str = Field(min_length=1, max_length=255)


class DirectionAdminRead(AdminWriteModel):
    direction_code: str
    direction_name: str


class ExamOptionWrite(AdminWriteModel):
    option_order: int = Field(ge=1)
    exam_subject_id: int = Field(gt=0)


class ExamOptionAdminRead(AdminWriteModel):
    option_order: int
    subject: ExamSubjectAdminRead


class ExamUnitWrite(AdminWriteModel):
    exam_unit: int = Field(ge=1, le=4)
    options: list[ExamOptionWrite] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_options(self) -> "ExamUnitWrite":
        orders = [item.option_order for item in self.options]
        subjects = [item.exam_subject_id for item in self.options]
        if len(orders) != len(set(orders)):
            raise ValueError("duplicate option_order in exam_unit")
        if len(subjects) != len(set(subjects)):
            raise ValueError("duplicate exam_subject_id in exam_unit")
        return self


class ExamUnitAdminRead(AdminWriteModel):
    exam_unit: int
    options: list[ExamOptionAdminRead]


class CatalogShellCreate(AdminWriteModel):
    school_id: int = Field(gt=0)
    college_id: int = Field(gt=0)
    major_id: int = Field(gt=0)
    admission_year: int = Field(ge=2000)
    study_mode: StudyMode


class CatalogAggregatePut(AdminWriteModel):
    school_id: int = Field(gt=0)
    college_id: int = Field(gt=0)
    major_id: int = Field(gt=0)
    admission_year: int = Field(ge=2000)
    study_mode: StudyMode
    directions: list[DirectionWrite]
    exam_units: list[ExamUnitWrite]

    @field_validator("directions", "exam_units")
    @classmethod
    def reject_null_collections(cls, value: object) -> object:
        return _reject_null(value)

    @model_validator(mode="after")
    def unique_collections(self) -> "CatalogAggregatePut":
        codes = [item.direction_code for item in self.directions]
        if len(codes) != len(set(codes)):
            raise ValueError("duplicate direction_code")
        units = [item.exam_unit for item in self.exam_units]
        if len(units) != len(set(units)):
            raise ValueError("duplicate exam_unit")
        return self


class CatalogAdminSummary(AdminWriteModel):
    id: int
    admission_year: int
    study_mode: StudyMode
    is_active: bool
    school: SchoolAdminRead
    college: CollegeAdminRead
    major: MajorAdminRead


class CatalogAdminDetail(CatalogAdminSummary):
    directions: list[DirectionAdminRead]
    exam_units: list[ExamUnitAdminRead]


__all__ = [
    "CatalogAdminDetail",
    "CatalogAdminSummary",
    "CatalogAggregatePut",
    "CatalogShellCreate",
    "DirectionAdminRead",
    "DirectionWrite",
    "ExamOptionAdminRead",
    "ExamOptionWrite",
    "ExamUnitAdminRead",
    "ExamUnitWrite",
    "Page",
]
