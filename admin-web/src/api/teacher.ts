import { getJson, postJson, type RequestOptions } from './client'
import type {
  AvailabilityStatus,
  Page,
  StatusFilter,
  StudyMode,
  TeacherAdminDetail,
  TeacherAdminSummary,
  VerificationStatus,
} from './types'

const ADMIN = '/api/v1/admin'

function withQuery(
  path: string,
  params: Record<string, string | number | undefined>,
): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '') {
      continue
    }
    search.set(key, String(value))
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

export type TeacherCreateBody = {
  display_name: string
  bio?: string | null
}

export type TeacherListQuery = {
  q?: string
  status?: StatusFilter
  availability?: AvailabilityStatus
  verification?: VerificationStatus
  schoolId?: number
  collegeId?: number
  majorId?: number
  admissionYear?: number
  studyMode?: StudyMode
  examSubjectId?: number
  page?: number
  pageSize?: number
}

// subject_school_id is a list-page lookup only. Do not add it here or map it to school_id.
export function listTeacherProfiles(
  query: TeacherListQuery = {},
  options?: RequestOptions,
): Promise<Page<TeacherAdminSummary>> {
  const q = query.q?.trim()
  return getJson(
    withQuery(`${ADMIN}/teacher-profiles`, {
      q: q ? q : undefined,
      status: query.status ?? 'all',
      availability: query.availability,
      verification: query.verification,
      school_id: query.schoolId,
      college_id: query.collegeId,
      major_id: query.majorId,
      admission_year: query.admissionYear,
      study_mode: query.studyMode,
      exam_subject_id: query.examSubjectId,
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    }),
    options,
  )
}

export function getTeacherProfile(
  teacherId: number,
  options?: RequestOptions,
): Promise<TeacherAdminDetail> {
  return getJson(`${ADMIN}/teacher-profiles/${teacherId}`, options)
}

export function createTeacher(
  body: TeacherCreateBody,
): Promise<TeacherAdminDetail> {
  return postJson(`${ADMIN}/teacher-profiles`, body)
}
