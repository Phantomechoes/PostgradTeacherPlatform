import { Select } from 'antd'
import type { ExamSubjectAdmin } from '../../api/types'
import { subjectLabel } from './labels'

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
  const byId = new Map<number, ExamSubjectAdmin>()
  for (const subject of subjects) {
    byId.set(subject.id, subject)
  }
  for (const extra of extras) {
    if (extra.school_id === null || extra.school_id === schoolId) {
      byId.set(extra.id, extra)
    }
  }
  if (value !== null && !byId.has(value)) {
    const current = extras.find((item) => item.id === value)
    if (current) {
      byId.set(current.id, current)
    }
  }
  const national = [...byId.values()].filter((item) => item.school_id === null)
  const school = [...byId.values()].filter((item) => item.school_id !== null)
  const groups = [
    national.length
      ? {
          label: '全国统考科目',
          options: national.map((item) => ({
            value: item.id,
            label: subjectLabel(item),
          })),
        }
      : null,
    school.length
      ? {
          label: '本校自命题科目',
          options: school.map((item) => ({
            value: item.id,
            label: subjectLabel(item),
          })),
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
