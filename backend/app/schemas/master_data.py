from typing import Literal

from pydantic import BaseModel

DegreeType = Literal["academic", "professional"]
StudyMode = Literal["full_time", "part_time"]


class SchoolSummary(BaseModel):
    id: int
    school_code: str
    name: str


class CollegeSummary(BaseModel):
    id: int
    college_code: str | None
    name: str


class MajorSummary(BaseModel):
    id: int
    major_code: str
    name: str
    degree_type: DegreeType


class ExamSubjectSummary(BaseModel):
    id: int
    subject_code: str
    name: str
    school_id: int | None


class DirectionRead(BaseModel):
    id: int
    direction_code: str
    direction_name: str


class ExamSubjectOptionRead(BaseModel):
    option_order: int
    subject: ExamSubjectSummary


class ExamUnitRead(BaseModel):
    exam_unit: int
    options: list[ExamSubjectOptionRead]


class AdmissionCatalogSummary(BaseModel):
    id: int
    admission_year: int
    study_mode: StudyMode
    school: SchoolSummary
    college: CollegeSummary
    major: MajorSummary


class AdmissionCatalogDetail(AdmissionCatalogSummary):
    directions: list[DirectionRead]
    exam_units: list[ExamUnitRead]


class AdmissionYearsRead(BaseModel):
    items: list[int]


class Page[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int
