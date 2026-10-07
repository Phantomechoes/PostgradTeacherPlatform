export type StatusFilter = 'all' | 'active' | 'inactive'

export type Page<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
}

export type SchoolAdmin = {
  id: number
  school_code: string
  name: string
  is_active: boolean
}

export type CollegeAdmin = {
  id: number
  school_id: number
  college_code: string | null
  name: string
  is_active: boolean
}

export type DegreeType = 'academic' | 'professional'

export type MajorAdmin = {
  id: number
  school_id: number
  major_code: string
  name: string
  degree_type: DegreeType
  is_active: boolean
}

export type ExamSubjectAdmin = {
  id: number
  school_id: number | null
  subject_code: string
  name: string
  is_active: boolean
}

export type StudyMode = 'full_time' | 'part_time'

export type DirectionAdmin = {
  direction_code: string
  direction_name: string
}

export type ExamOptionAdmin = {
  option_order: number
  subject: ExamSubjectAdmin
}

export type ExamUnitAdmin = {
  exam_unit: number
  options: ExamOptionAdmin[]
}

export type CatalogAdminSummary = {
  id: number
  admission_year: number
  study_mode: StudyMode
  is_active: boolean
  school: SchoolAdmin
  college: CollegeAdmin
  major: MajorAdmin
}

export type CatalogAdminDetail = CatalogAdminSummary & {
  directions: DirectionAdmin[]
  exam_units: ExamUnitAdmin[]
}

export type CatalogShellCreate = {
  school_id: number
  college_id: number
  major_id: number
  admission_year: number
  study_mode: StudyMode
}

export type DirectionWrite = {
  direction_code: string
  direction_name: string
}

export type ExamOptionWrite = {
  option_order: number
  exam_subject_id: number
}

export type ExamUnitWrite = {
  exam_unit: number
  options: ExamOptionWrite[]
}

export type CatalogAggregatePut = CatalogShellCreate & {
  directions: DirectionWrite[]
  exam_units: ExamUnitWrite[]
}

export type AvailabilityStatus = 'unknown' | 'available' | 'unavailable'

export type VerificationStatus = 'unverified' | 'verified' | 'rejected'

export type TeacherAdminSummary = {
  id: number
  display_name: string
  bio: string | null
  is_active: boolean
  availability_status: AvailabilityStatus
  verification_status: VerificationStatus
}

export type AdmissionRecordAdmin = {
  id: number
  teacher_profile_id: number
  school: SchoolAdmin
  college: CollegeAdmin
  major: MajorAdmin
  admission_year: number
  study_mode: StudyMode
  admission_catalog_id: number | null
  initial_total: number | null
  retest_total: number | null
  final_total: number | null
  is_active: boolean
}

export type TeacherAdminDetail = TeacherAdminSummary & {
  admission_records: AdmissionRecordAdmin[]
  teach_subjects: ExamSubjectAdmin[]
}
