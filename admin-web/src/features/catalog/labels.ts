import type { ExamSubjectAdmin, StudyMode } from '../../api/types'

export const STUDY_MODE_LABEL: Record<StudyMode, string> = {
  full_time: '全日制',
  part_time: '非全日制',
}

export function subjectLabel(subject: ExamSubjectAdmin): string {
  const scope = subject.school_id === null ? '全国' : '本校'
  const status = subject.is_active ? '' : ' · 已停用'
  return `${subject.subject_code} ${subject.name}（${scope}${status}）`
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
