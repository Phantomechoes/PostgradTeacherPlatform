import { getJson, patchJson, postJson, type RequestOptions } from './client'
import type {
  CollegeAdmin,
  DegreeType,
  ExamSubjectAdmin,
  MajorAdmin,
  Page,
  SchoolAdmin,
  StatusFilter,
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

export type SchoolWrite = {
  school_code: string
  name: string
}

export type CollegeWrite = {
  college_code: string | null
  name: string
}

export type MajorWrite = {
  major_code: string
  name: string
  degree_type: DegreeType
}

export type SubjectWrite = {
  subject_code: string
  name: string
}

export async function listAllSchools(
  status: StatusFilter = 'all',
  options?: RequestOptions,
): Promise<SchoolAdmin[]> {
  const items: SchoolAdmin[] = []
  let page = 1
  for (;;) {
    const result = await listSchools({ status, page, pageSize: 100 }, options)
    items.push(...result.items)
    if (items.length >= result.total || result.items.length === 0) {
      break
    }
    page += 1
  }
  return items
}

export function listSchools(
  query: {
    q?: string
    status?: StatusFilter
    page?: number
    pageSize?: number
  } = {},
  options?: RequestOptions,
): Promise<Page<SchoolAdmin>> {
  const q = query.q?.trim()
  return getJson(
    withQuery(`${ADMIN}/schools`, {
      q: q ? q : undefined,
      status: query.status ?? 'all',
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    }),
    options,
  )
}

export function getSchool(
  schoolId: number,
  options?: RequestOptions,
): Promise<SchoolAdmin> {
  return getJson(`${ADMIN}/schools/${schoolId}`, options)
}

export function createSchool(body: SchoolWrite): Promise<SchoolAdmin> {
  return postJson(`${ADMIN}/schools`, body)
}

export function updateSchool(
  schoolId: number,
  body: SchoolWrite,
): Promise<SchoolAdmin> {
  return patchJson(`${ADMIN}/schools/${schoolId}`, body)
}

export function setSchoolStatus(
  schoolId: number,
  isActive: boolean,
): Promise<SchoolAdmin> {
  return patchJson(`${ADMIN}/schools/${schoolId}/status`, {
    is_active: isActive,
  })
}

export function listColleges(
  schoolId: number,
  status: StatusFilter = 'all',
  options?: RequestOptions,
): Promise<CollegeAdmin[]> {
  return getJson(
    withQuery(`${ADMIN}/schools/${schoolId}/colleges`, { status }),
    options,
  )
}

export function createCollege(
  schoolId: number,
  body: CollegeWrite,
): Promise<CollegeAdmin> {
  return postJson(`${ADMIN}/schools/${schoolId}/colleges`, body)
}

export function updateCollege(
  collegeId: number,
  body: CollegeWrite,
): Promise<CollegeAdmin> {
  return patchJson(`${ADMIN}/colleges/${collegeId}`, body)
}

export function setCollegeStatus(
  collegeId: number,
  isActive: boolean,
): Promise<CollegeAdmin> {
  return patchJson(`${ADMIN}/colleges/${collegeId}/status`, {
    is_active: isActive,
  })
}

export function listMajors(
  schoolId: number,
  status: StatusFilter = 'all',
  options?: RequestOptions,
): Promise<MajorAdmin[]> {
  return getJson(
    withQuery(`${ADMIN}/schools/${schoolId}/majors`, { status }),
    options,
  )
}

export function createMajor(
  schoolId: number,
  body: MajorWrite,
): Promise<MajorAdmin> {
  return postJson(`${ADMIN}/schools/${schoolId}/majors`, body)
}

export function updateMajor(
  majorId: number,
  body: MajorWrite,
): Promise<MajorAdmin> {
  return patchJson(`${ADMIN}/majors/${majorId}`, body)
}

export function setMajorStatus(
  majorId: number,
  isActive: boolean,
): Promise<MajorAdmin> {
  return patchJson(`${ADMIN}/majors/${majorId}/status`, { is_active: isActive })
}

export function listNationalSubjects(
  status: StatusFilter = 'all',
  options?: RequestOptions,
): Promise<ExamSubjectAdmin[]> {
  return getJson(
    withQuery(`${ADMIN}/exam-subjects/national`, { status }),
    options,
  )
}

export function listSchoolSubjects(
  schoolId: number,
  status: StatusFilter = 'all',
  options?: RequestOptions,
): Promise<ExamSubjectAdmin[]> {
  return getJson(
    withQuery(`${ADMIN}/schools/${schoolId}/exam-subjects`, { status }),
    options,
  )
}

export function createNationalSubject(
  body: SubjectWrite,
): Promise<ExamSubjectAdmin> {
  return postJson(`${ADMIN}/exam-subjects/national`, body)
}

export function createSchoolSubject(
  schoolId: number,
  body: SubjectWrite,
): Promise<ExamSubjectAdmin> {
  return postJson(`${ADMIN}/schools/${schoolId}/exam-subjects`, body)
}

export function updateSubject(
  subjectId: number,
  body: SubjectWrite,
): Promise<ExamSubjectAdmin> {
  return patchJson(`${ADMIN}/exam-subjects/${subjectId}`, body)
}

export function setSubjectStatus(
  subjectId: number,
  isActive: boolean,
): Promise<ExamSubjectAdmin> {
  return patchJson(`${ADMIN}/exam-subjects/${subjectId}/status`, {
    is_active: isActive,
  })
}
