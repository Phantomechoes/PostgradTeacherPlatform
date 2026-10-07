import type { ExamSubjectAdmin } from '../../api/types'

export function sortTeachSubjects(
  subjects: readonly ExamSubjectAdmin[],
): ExamSubjectAdmin[] {
  return [...subjects].sort((left, right) => left.id - right.id)
}

export function teachSubjectIds(ids: readonly number[]): number[] {
  return [...new Set(ids.filter((id) => Number.isInteger(id) && id > 0))].sort(
    (left, right) => left - right,
  )
}

export function sameTeachSubjectIds(
  left: readonly number[],
  right: readonly number[],
): boolean {
  const normalizedLeft = teachSubjectIds(left)
  const normalizedRight = teachSubjectIds(right)
  return (
    normalizedLeft.length === normalizedRight.length &&
    normalizedLeft.every((id, index) => id === normalizedRight[index])
  )
}

export function addedTeachSubjectIds(
  baselineIds: readonly number[],
  draftIds: readonly number[],
): number[] {
  const existing = new Set(teachSubjectIds(baselineIds))
  return teachSubjectIds(draftIds).filter((id) => !existing.has(id))
}

export function teachSubjectKind(subject: ExamSubjectAdmin): string {
  return subject.school_id === null ? '全国统考' : '学校自命题'
}
