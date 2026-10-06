import type {
  AdmissionRecordCreateBody,
  AdmissionRecordPatch,
} from '../../api/teacher'
import type {
  AdmissionRecordAdmin,
  CatalogAdminSummary,
  CollegeAdmin,
  MajorAdmin,
  SchoolAdmin,
  StudyMode,
  TeacherAdminDetail,
} from '../../api/types'
import { entityLabel } from '../catalog/labels'

export type AdmissionFormValues = {
  school_id?: number
  college_id?: number
  major_id?: number
  admission_year?: number | null
  study_mode?: StudyMode
  admission_catalog_id?: number | null
  initial_total?: number | null
  retest_total?: number | null
  final_total?: number | null
}

export type ReferenceOption = {
  value: number
  label: string
  disabled: boolean
}

type IdentityLink = {
  school_id?: number
  college_id?: number
  major_id?: number
  admission_year?: number
  study_mode?: StudyMode
}

export function emptyAdmissionFormValues(): AdmissionFormValues {
  return {
    admission_catalog_id: null,
    initial_total: null,
    retest_total: null,
    final_total: null,
  }
}

export function toAdmissionFormValues(
  record: AdmissionRecordAdmin,
): AdmissionFormValues {
  return {
    school_id: record.school.id,
    college_id: record.college.id,
    major_id: record.major.id,
    admission_year: record.admission_year,
    study_mode: record.study_mode,
    admission_catalog_id: record.admission_catalog_id,
    initial_total: record.initial_total,
    retest_total: record.retest_total,
    final_total: record.final_total,
  }
}

export function identityLinkFrom(values: AdmissionFormValues): IdentityLink {
  return {
    school_id: values.school_id,
    college_id: values.college_id,
    major_id: values.major_id,
    admission_year:
      typeof values.admission_year === 'number'
        ? values.admission_year
        : undefined,
    study_mode: values.study_mode,
  }
}

export function sortAdmissionRecords(
  records: readonly AdmissionRecordAdmin[],
): AdmissionRecordAdmin[] {
  return [...records].sort((left, right) => {
    if (left.is_active !== right.is_active) {
      return left.is_active ? -1 : 1
    }
    if (left.admission_year !== right.admission_year) {
      return right.admission_year - left.admission_year
    }
    return left.id - right.id
  })
}

export function upsertAdmissionRecord(
  detail: TeacherAdminDetail,
  admission: AdmissionRecordAdmin,
): TeacherAdminDetail {
  const rest = detail.admission_records.filter(
    (record) => record.id !== admission.id,
  )
  return {
    ...detail,
    admission_records: sortAdmissionRecords([...rest, admission]),
  }
}

function scoreValue(value: number | null | undefined): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null
  }
  return value
}

function sameScore(left: number | null, right: number | null): boolean {
  if (left === null || right === null) {
    return left === right
  }
  return (
    Math.round((left + Number.EPSILON) * 100) ===
    Math.round((right + Number.EPSILON) * 100)
  )
}

function catalogValue(value: number | null | undefined): number | null {
  return typeof value === 'number' ? value : null
}

export function buildAdmissionCreate(
  values: AdmissionFormValues,
): AdmissionRecordCreateBody | null {
  if (
    typeof values.school_id !== 'number' ||
    typeof values.college_id !== 'number' ||
    typeof values.major_id !== 'number' ||
    typeof values.admission_year !== 'number' ||
    values.study_mode === undefined
  ) {
    return null
  }
  const body: AdmissionRecordCreateBody = {
    school_id: values.school_id,
    college_id: values.college_id,
    major_id: values.major_id,
    admission_year: values.admission_year,
    study_mode: values.study_mode,
  }
  const catalog = catalogValue(values.admission_catalog_id)
  if (catalog !== null) {
    body.admission_catalog_id = catalog
  }
  const initial = scoreValue(values.initial_total)
  const retest = scoreValue(values.retest_total)
  const finalTotal = scoreValue(values.final_total)
  if (initial !== null) {
    body.initial_total = initial
  }
  if (retest !== null) {
    body.retest_total = retest
  }
  if (finalTotal !== null) {
    body.final_total = finalTotal
  }
  return body
}

// Unchanged identity ids stay omitted so inactive historical refs are not resent.
export function buildAdmissionPatch(
  current: AdmissionRecordAdmin,
  values: AdmissionFormValues,
): AdmissionRecordPatch | null {
  const patch: AdmissionRecordPatch = {}
  if (
    typeof values.school_id === 'number' &&
    values.school_id !== current.school.id
  ) {
    patch.school_id = values.school_id
  }
  if (
    typeof values.college_id === 'number' &&
    values.college_id !== current.college.id
  ) {
    patch.college_id = values.college_id
  }
  if (
    typeof values.major_id === 'number' &&
    values.major_id !== current.major.id
  ) {
    patch.major_id = values.major_id
  }
  if (
    typeof values.admission_year === 'number' &&
    values.admission_year !== current.admission_year
  ) {
    patch.admission_year = values.admission_year
  }
  if (
    values.study_mode !== undefined &&
    values.study_mode !== current.study_mode
  ) {
    patch.study_mode = values.study_mode
  }
  const catalog = catalogValue(values.admission_catalog_id)
  if (catalog !== current.admission_catalog_id) {
    patch.admission_catalog_id = catalog
  }
  const initial = scoreValue(values.initial_total)
  const retest = scoreValue(values.retest_total)
  const finalTotal = scoreValue(values.final_total)
  if (!sameScore(initial, current.initial_total)) {
    patch.initial_total = initial
  }
  if (!sameScore(retest, current.retest_total)) {
    patch.retest_total = retest
  }
  if (!sameScore(finalTotal, current.final_total)) {
    patch.final_total = finalTotal
  }
  return Object.keys(patch).length === 0 ? null : patch
}

export function schoolOptionLabel(school: SchoolAdmin): string {
  return entityLabel(school.school_code, school.name, school.is_active)
}

export function collegeOptionLabel(college: CollegeAdmin): string {
  return entityLabel(college.college_code, college.name, college.is_active)
}

export function majorOptionLabel(major: MajorAdmin): string {
  return entityLabel(major.major_code, major.name, major.is_active)
}

export function catalogOptionLabel(catalog: {
  id: number
  is_active: boolean
}): string {
  const status = catalog.is_active ? '已公开' : '未公开'
  return `招生目录 #${catalog.id}（${status}）`
}

export function withCurrentReference<
  T extends { id: number; is_active: boolean },
>(
  activeItems: readonly T[],
  current: T | null,
  selectedId: number | undefined,
  label: (item: T) => string,
): ReferenceOption[] {
  const options = activeItems.map((item) => ({
    value: item.id,
    label: label(item),
    disabled: false,
  }))
  if (
    current &&
    !current.is_active &&
    selectedId === current.id &&
    !options.some((option) => option.value === current.id)
  ) {
    options.unshift({
      value: current.id,
      label: label(current),
      disabled: true,
    })
  }
  return options
}

export function catalogSelectOptions(
  catalogs: readonly CatalogAdminSummary[],
  selectedId: number | null | undefined,
  current: { id: number; is_active: boolean } | null,
): { value: number; label: string }[] {
  const options = catalogs.map((catalog) => ({
    value: catalog.id,
    label: catalogOptionLabel(catalog),
  }))
  if (
    typeof selectedId === 'number' &&
    !options.some((option) => option.value === selectedId)
  ) {
    const known = current && current.id === selectedId ? current : null
    options.unshift({
      value: selectedId,
      label: known ? catalogOptionLabel(known) : `招生目录 #${selectedId}`,
    })
  }
  return options
}

export function formatScore(value: number | null): string {
  return value === null ? '—' : String(value)
}
