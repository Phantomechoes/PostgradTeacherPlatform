from app.models.admission_catalog import AdmissionCatalog
from app.models.admission_catalog_direction import AdmissionCatalogDirection
from app.models.admission_catalog_exam_subject import AdmissionCatalogExamSubject
from app.models.admission_record import AdmissionRecord
from app.models.college import College
from app.models.exam_subject import ExamSubject
from app.models.major import Major
from app.models.school import School
from app.models.teacher_profile import TeacherProfile
from app.models.teacher_teach_subject import TeacherTeachSubject

__all__ = [
    "AdmissionCatalog",
    "AdmissionCatalogDirection",
    "AdmissionCatalogExamSubject",
    "AdmissionRecord",
    "College",
    "ExamSubject",
    "Major",
    "School",
    "TeacherProfile",
    "TeacherTeachSubject",
]
