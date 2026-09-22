import type {
  CatalogAdminDetail,
  CatalogAggregatePut,
  ExamSubjectAdmin,
  StudyMode,
} from '../../api/types'
import { newRowKey } from './labels'

export type DirectionDraft = {
  key: string
  direction_code: string
  direction_name: string
}

export type OptionDraft = {
  key: string
  option_order: number
  exam_subject_id: number | null
}

export type UnitDraft = {
  key: string
  exam_unit: number
  options: OptionDraft[]
}

export type CatalogDraft = {
  schoolId: number
  collegeId: number
  majorId: number
  admissionYear: number
  studyMode: StudyMode
  directions: DirectionDraft[]
  units: UnitDraft[]
}

export function draftFromDetail(detail: CatalogAdminDetail): CatalogDraft {
  return {
    schoolId: detail.school.id,
    collegeId: detail.college.id,
    majorId: detail.major.id,
    admissionYear: detail.admission_year,
    studyMode: detail.study_mode,
    directions: detail.directions.map((item) => ({
      key: newRowKey(),
      direction_code: item.direction_code,
      direction_name: item.direction_name,
    })),
    units: detail.exam_units.map((unit) => ({
      key: newRowKey(),
      exam_unit: unit.exam_unit,
      options: unit.options.map((option) => ({
        key: newRowKey(),
        option_order: option.option_order,
        exam_subject_id: option.subject.id,
      })),
    })),
  }
}

export function putFromDetail(detail: CatalogAdminDetail): CatalogAggregatePut {
  return {
    school_id: detail.school.id,
    college_id: detail.college.id,
    major_id: detail.major.id,
    admission_year: detail.admission_year,
    study_mode: detail.study_mode,
    directions: detail.directions.map((item) => ({
      direction_code: item.direction_code,
      direction_name: item.direction_name,
    })),
    exam_units: detail.exam_units.map((unit) => ({
      exam_unit: unit.exam_unit,
      options: unit.options.map((option) => ({
        option_order: option.option_order,
        exam_subject_id: option.subject.id,
      })),
    })),
  }
}

export function buildPut(
  draft: CatalogDraft,
): { ok: true; body: CatalogAggregatePut } | { ok: false; error: string } {
  const directions: CatalogAggregatePut['directions'] = []
  const seenCodes = new Set<string>()
  for (const row of draft.directions) {
    const code = row.direction_code.trim()
    const name = row.direction_name.trim()
    if (!code && !name) {
      continue
    }
    if (!code || !name) {
      return { ok: false, error: '研究方向的代码和名称都需要填写' }
    }
    if (seenCodes.has(code)) {
      return { ok: false, error: '研究方向代码不能重复' }
    }
    seenCodes.add(code)
    directions.push({ direction_code: code, direction_name: name })
  }

  const examUnits: CatalogAggregatePut['exam_units'] = []
  const seenUnits = new Set<number>()
  for (const unit of draft.units) {
    const filled = unit.options.filter(
      (option) => option.exam_subject_id !== null,
    )
    if (filled.length === 0) {
      continue
    }
    if (seenUnits.has(unit.exam_unit)) {
      return { ok: false, error: '考试单元不能重复' }
    }
    seenUnits.add(unit.exam_unit)
    const orders = new Set<number>()
    const subjects = new Set<number>()
    const options: CatalogAggregatePut['exam_units'][number]['options'] = []
    for (const option of filled) {
      if (option.option_order < 1) {
        return { ok: false, error: 'option_order 必须大于等于 1' }
      }
      if (orders.has(option.option_order)) {
        return { ok: false, error: '同一考试单元的 option_order 不能重复' }
      }
      const subjectId = option.exam_subject_id
      if (subjectId === null) {
        return { ok: false, error: '请为每个科目选项选择科目' }
      }
      if (subjects.has(subjectId)) {
        return { ok: false, error: '同一考试单元不能重复选择同一科目' }
      }
      orders.add(option.option_order)
      subjects.add(subjectId)
      options.push({
        option_order: option.option_order,
        exam_subject_id: subjectId,
      })
    }
    examUnits.push({ exam_unit: unit.exam_unit, options })
  }

  return {
    ok: true,
    body: {
      school_id: draft.schoolId,
      college_id: draft.collegeId,
      major_id: draft.majorId,
      admission_year: draft.admissionYear,
      study_mode: draft.studyMode,
      directions,
      exam_units: examUnits,
    },
  }
}

export function samePut(
  left: CatalogAggregatePut,
  right: CatalogAggregatePut,
): boolean {
  return JSON.stringify(left) === JSON.stringify(right)
}

export function referencedSubjects(
  detail: CatalogAdminDetail,
): ExamSubjectAdmin[] {
  const map = new Map<number, ExamSubjectAdmin>()
  for (const unit of detail.exam_units) {
    for (const option of unit.options) {
      map.set(option.subject.id, option.subject)
    }
  }
  return [...map.values()]
}
