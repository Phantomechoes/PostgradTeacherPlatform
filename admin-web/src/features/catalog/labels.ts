import type { ExamSubjectAdmin, StudyMode } from '../../api/types'

export const STUDY_MODE_LABEL: Record<StudyMode, string> = {
  full_time: '全日制',
  part_time: '非全日制',
}

export const FOREIGN_SUBJECT_HINT = '历史外校科目，当前院校不可用'

export function subjectLabel(
  subject: ExamSubjectAdmin,
  schoolId?: number,
): string {
  const status = subject.is_active ? '' : ' · 已停用'
  if (subject.school_id === null) {
    return `${subject.subject_code} ${subject.name}（全国${status}）`
  }
  if (schoolId !== undefined && subject.school_id !== schoolId) {
    return `${subject.subject_code} ${subject.name}（${FOREIGN_SUBJECT_HINT}${status}）`
  }
  return `${subject.subject_code} ${subject.name}（本校${status}）`
}

export function entityLabel(
  code: string | null,
  name: string,
  active: boolean,
): string {
  const prefix = code ? `${code} ` : ''
  return `${prefix}${name}${active ? '' : '（已停用）'}`
}

export function newRowKey(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}
