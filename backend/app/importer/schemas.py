from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.master_data import DegreeType, StudyMode


class ImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _strip_nonempty(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


class SchoolImport(ImportModel):
    school_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("school_code", "name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


class CollegeImport(ImportModel):
    school_code: str = Field(min_length=1, max_length=32)
    college_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("school_code", "college_code", "name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


class MajorImport(ImportModel):
    school_code: str = Field(min_length=1, max_length=32)
    major_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    degree_type: DegreeType

    @field_validator("school_code", "major_code", "name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


class NationalSubjectImport(ImportModel):
    scope: Literal["national"]
    subject_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("subject_code", "name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


class SchoolSubjectImport(ImportModel):
    scope: Literal["school"]
    school_code: str = Field(min_length=1, max_length=32)
    subject_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)

    @field_validator("school_code", "subject_code", "name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


ExamSubjectImport = Annotated[
    NationalSubjectImport | SchoolSubjectImport,
    Field(discriminator="scope"),
]


class DirectionImport(ImportModel):
    direction_code: str = Field(min_length=1, max_length=32)
    direction_name: str = Field(min_length=1, max_length=255)

    @field_validator("direction_code", "direction_name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


class NationalOptionImport(ImportModel):
    option_order: int = Field(ge=1)
    subject_scope: Literal["national"]
    subject_code: str = Field(min_length=1, max_length=32)

    @field_validator("subject_code")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


class SchoolOptionImport(ImportModel):
    option_order: int = Field(ge=1)
    subject_scope: Literal["school"]
    school_code: str = Field(min_length=1, max_length=32)
    subject_code: str = Field(min_length=1, max_length=32)

    @field_validator("school_code", "subject_code")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


ExamOptionImport = Annotated[
    NationalOptionImport | SchoolOptionImport,
    Field(discriminator="subject_scope"),
]


class ExamUnitImport(ImportModel):
    exam_unit: int = Field(ge=1, le=4)
    options: list[ExamOptionImport] = Field(min_length=1)


class CatalogImport(ImportModel):
    school_code: str = Field(min_length=1, max_length=32)
    college_code: str = Field(min_length=1, max_length=32)
    major_code: str = Field(min_length=1, max_length=32)
    admission_year: int = Field(ge=2000)
    study_mode: StudyMode
    directions: list[DirectionImport]
    exam_units: list[ExamUnitImport]

    @field_validator("school_code", "college_code", "major_code")
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)


class ImportDocument(ImportModel):
    schema_version: Literal[1]
    schools: list[SchoolImport]
    colleges: list[CollegeImport]
    majors: list[MajorImport]
    exam_subjects: list[ExamSubjectImport]
    catalogs: list[CatalogImport]


class ImportManifest(ImportModel):
    schema_version: Literal[1]
    dataset_id: str = Field(min_length=1, max_length=64)
    data_kind: str = Field(min_length=1, max_length=64)
    source_type: Literal["synthetic"]
    source_description: str = Field(min_length=1, max_length=512)
    publisher: str = Field(min_length=1, max_length=255)
    retrieved_at: str = Field(min_length=1, max_length=32)
    verification_status: Literal["approved"]

    @field_validator(
        "dataset_id",
        "data_kind",
        "source_description",
        "publisher",
        "retrieved_at",
    )
    @classmethod
    def nonempty(cls, value: str) -> str:
        return _strip_nonempty(value)
