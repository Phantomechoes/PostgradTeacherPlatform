import {
  getJson,
  patchJson,
  postJson,
  putJson,
  type RequestOptions,
} from './client'
import type {
  CatalogAdminDetail,
  CatalogAdminSummary,
  CatalogAggregatePut,
  CatalogShellCreate,
  Page,
  StatusFilter,
  StudyMode,
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

export type CatalogListQuery = {
  schoolId: number
  status?: StatusFilter
  admissionYear?: number
  collegeId?: number
  majorId?: number
  studyMode?: StudyMode
  page?: number
  pageSize?: number
}

export function listCatalogs(
  query: CatalogListQuery,
  options?: RequestOptions,
): Promise<Page<CatalogAdminSummary>> {
  return getJson(
    withQuery(`${ADMIN}/admission-catalogs`, {
      school_id: query.schoolId,
      status: query.status ?? 'all',
      admission_year: query.admissionYear,
      college_id: query.collegeId,
      major_id: query.majorId,
      study_mode: query.studyMode,
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
    }),
    options,
  )
}

export function getCatalog(
  catalogId: number,
  options?: RequestOptions,
): Promise<CatalogAdminDetail> {
  return getJson(`${ADMIN}/admission-catalogs/${catalogId}`, options)
}

export function createCatalogShell(
  body: CatalogShellCreate,
): Promise<CatalogAdminDetail> {
  return postJson(`${ADMIN}/admission-catalogs`, body)
}

export function replaceCatalogAggregate(
  catalogId: number,
  body: CatalogAggregatePut,
): Promise<CatalogAdminDetail> {
  return putJson(`${ADMIN}/admission-catalogs/${catalogId}`, body)
}

export function setCatalogStatus(
  catalogId: number,
  isActive: boolean,
): Promise<CatalogAdminDetail> {
  return patchJson(`${ADMIN}/admission-catalogs/${catalogId}/status`, {
    is_active: isActive,
  })
}
