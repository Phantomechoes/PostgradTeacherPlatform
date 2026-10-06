import { getJson, patchJson, postJson, type RequestOptions } from './client'
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

export type TeacherProfilePatch = {
  display_name?: string
  bio?: string | null
}

export type TeacherStatusPatch = {
  is_active: boolean
}

export type TeacherAvailabilityPatch = {
  availability_status: AvailabilityStatus
}

export type TeacherVerificationPatch = {
  verification_status: VerificationStatus
}

export function updateTeacherProfile(
  teacherId: number,
  body: TeacherProfilePatch,
): Promise<TeacherAdminSummary> {
  return patchJson(`${ADMIN}/teacher-profiles/${teacherId}`, body)
}

export function setTeacherStatus(
  teacherId: number,
  isActive: boolean,
): Promise<TeacherAdminSummary> {
  const body: TeacherStatusPatch = { is_active: isActive }
  return patchJson(`${ADMIN}/teacher-profiles/${teacherId}/status`, body)
}

export function setTeacherAvailability(
  teacherId: number,
  availabilityStatus: AvailabilityStatus,
): Promise<TeacherAdminSummary> {
  const body: TeacherAvailabilityPatch = {
    availability_status: availabilityStatus,
  }
  return patchJson(`${ADMIN}/teacher-profiles/${teacherId}/availability`, body)
}

export function setTeacherVerification(
  teacherId: number,
  verificationStatus: VerificationStatus,
): Promise<TeacherAdminSummary> {
  const body: TeacherVerificationPatch = {
    verification_status: verificationStatus,
  }
  return patchJson(`${ADMIN}/teacher-profiles/${teacherId}/verification`, body)
}
