import { Select } from 'antd'
import type { ExamSubjectAdmin } from '../../api/types'
import { FOREIGN_SUBJECT_HINT, subjectLabel } from './labels'

function isNational(subject: ExamSubjectAdmin): boolean {
  return subject.school_id === null
}

function isCurrentSchool(subject: ExamSubjectAdmin, schoolId: number): boolean {
  return subject.school_id === schoolId
}

export function SubjectPicker({
  value,
  schoolId,
  subjects,
  extras,
  onChange,
}: {
  value: number | null
  schoolId: number
  subjects: ExamSubjectAdmin[]
  extras: ExamSubjectAdmin[]
  onChange: (value: number) => void
}) {
  const candidates = new Map<number, ExamSubjectAdmin>()
  for (const subject of [...subjects, ...extras]) {
    if (isNational(subject) || isCurrentSchool(subject, schoolId)) {
      candidates.set(subject.id, subject)
    }
  }
  const selected =
    value === null
      ? undefined
      : (candidates.get(value) ??
        extras.find((item) => item.id === value) ??
        subjects.find((item) => item.id === value))
  const foreign =
    selected && !isNational(selected) && !isCurrentSchool(selected, schoolId)
      ? selected
      : undefined
  const national = [...candidates.values()].filter(isNational)
  const school = [...candidates.values()].filter((item) =>
    isCurrentSchool(item, schoolId),
  )
  const groups = [
    national.length
      ? {
          label: '全国统考科目',
          options: national.map((item) => ({
            value: item.id,
            label: subjectLabel(item, schoolId),
          })),
        }
      : null,
    school.length
      ? {
          label: '本校自命题科目',
          options: school.map((item) => ({
            value: item.id,
            label: subjectLabel(item, schoolId),
          })),
        }
      : null,
    foreign
      ? {
          label: FOREIGN_SUBJECT_HINT,
          options: [
            {
              value: foreign.id,
              label: subjectLabel(foreign, schoolId),
            },
          ],
        }
      : null,
  ].filter((group) => group !== null)
  return (
    <Select
      showSearch
      optionFilterProp="label"
      style={{ width: '100%' }}
      placeholder="选择科目"
      value={value ?? undefined}
      onChange={onChange}
      options={groups}
    />
  )
}
