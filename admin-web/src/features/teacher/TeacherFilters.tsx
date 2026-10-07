import {
  App,
  Button,
  Input,
  InputNumber,
  Select,
  Space,
  Typography,
} from 'antd'
import { useEffect, useState } from 'react'
import { ApiError, isAbortError } from '../../api/client'
import {
  listAllSchools,
  listColleges,
  listMajors,
  listNationalSubjects,
  listSchoolSubjects,
} from '../../api/masterData'
import type {
  AvailabilityStatus,
  CollegeAdmin,
  ExamSubjectAdmin,
  MajorAdmin,
  SchoolAdmin,
  StatusFilter,
  StudyMode,
  VerificationStatus,
} from '../../api/types'
import { StatusFilterSelect } from '../../components/StatusFilterSelect'
import { entityLabel, STUDY_MODE_LABEL, subjectLabel } from '../catalog/labels'
import {
  AVAILABILITY_LABEL,
  AVAILABILITY_VALUES,
  VERIFICATION_LABEL,
  VERIFICATION_VALUES,
} from './labels'

type FilterPatch = Record<string, string | null>

export function TeacherFilters({
  q,
  status,
  availability,
  verification,
  schoolId,
  collegeId,
  majorId,
  admissionYear,
  studyMode,
  examSubjectId,
  subjectSchoolId,
  onChange,
}: {
  q: string
  status: StatusFilter
  availability?: AvailabilityStatus
  verification?: VerificationStatus
  schoolId?: number
  collegeId?: number
  majorId?: number
  admissionYear?: number
  studyMode?: StudyMode
  examSubjectId?: number
  subjectSchoolId?: number
  onChange: (patch: FilterPatch) => void
}) {
  const { message } = App.useApp()
  const [draft, setDraft] = useState({ q, value: q })
  if (draft.q !== q) {
    setDraft({ q, value: q })
  }
  const hasMore = [
    schoolId,
    collegeId,
    majorId,
    admissionYear,
    studyMode,
    examSubjectId,
    subjectSchoolId,
  ].some((value) => value !== undefined)
  const [moreOpen, setMoreOpen] = useState(hasMore)
  const [schools, setSchools] = useState<SchoolAdmin[]>([])
  const [nationalSubjects, setNationalSubjects] = useState<ExamSubjectAdmin[]>(
    [],
  )
  const childKey = schoolId ?? 0
  const [childLists, setChildLists] = useState<{
    key: number
    colleges: CollegeAdmin[]
    majors: MajorAdmin[]
  }>({ key: childKey, colleges: [], majors: [] })
  if (childLists.key !== childKey) {
    setChildLists({ key: childKey, colleges: [], majors: [] })
  }
  const subjectKey = subjectSchoolId ?? 0
  const [schoolSubjects, setSchoolSubjects] = useState<{
    key: number
    items: ExamSubjectAdmin[]
  }>({ key: subjectKey, items: [] })
  if (schoolSubjects.key !== subjectKey) {
    setSchoolSubjects({ key: subjectKey, items: [] })
  }

  useEffect(() => {
    const controller = new AbortController()
    listAllSchools('all', { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) {
          setSchools(items)
        }
      })
      .catch((error: unknown) => {
        if (!isAbortError(error) && !controller.signal.aborted) {
          message.error(
            error instanceof ApiError ? error.message : '无法加载院校列表',
          )
        }
      })
    return () => controller.abort()
  }, [message])

  useEffect(() => {
    const controller = new AbortController()
    listNationalSubjects('all', { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) {
          setNationalSubjects(items)
        }
      })
      .catch((error: unknown) => {
        if (!isAbortError(error) && !controller.signal.aborted) {
          message.error(
            error instanceof ApiError ? error.message : '无法加载全国统考科目',
          )
        }
      })
    return () => controller.abort()
  }, [message])

  useEffect(() => {
    if (!schoolId) {
      return
    }
    const controller = new AbortController()
    const key = schoolId
    Promise.all([
      listColleges(schoolId, 'all', { signal: controller.signal }),
      listMajors(schoolId, 'all', { signal: controller.signal }),
    ])
      .then(([colleges, majors]) => {
        setChildLists((current) =>
          current.key === key ? { key, colleges, majors } : current,
        )
      })
      .catch((error: unknown) => {
        if (!isAbortError(error) && !controller.signal.aborted) {
          setChildLists((current) =>
            current.key === key ? { key, colleges: [], majors: [] } : current,
          )
          message.error(
            error instanceof ApiError ? error.message : '无法加载学院或专业',
          )
        }
      })
    return () => controller.abort()
  }, [message, schoolId])

  useEffect(() => {
    if (!subjectSchoolId) {
      return
    }
    const controller = new AbortController()
    const key = subjectSchoolId
    listSchoolSubjects(subjectSchoolId, 'all', { signal: controller.signal })
      .then((items) => {
        setSchoolSubjects((current) =>
          current.key === key ? { key, items } : current,
        )
      })
      .catch((error: unknown) => {
        if (!isAbortError(error) && !controller.signal.aborted) {
          setSchoolSubjects((current) =>
            current.key === key ? { key, items: [] } : current,
          )
          message.error(
            error instanceof ApiError ? error.message : '无法加载自命题科目',
          )
        }
      })
    return () => controller.abort()
  }, [message, subjectSchoolId])

  const knownSubjectIds = new Set<number>([
    ...nationalSubjects.map((item) => item.id),
    ...schoolSubjects.items.map((item) => item.id),
  ])
  const subjectGroups = [
    nationalSubjects.length
      ? {
          label: '全国统考科目',
          options: nationalSubjects.map((item) => ({
            value: item.id,
            label: subjectLabel(item),
          })),
        }
      : null,
    subjectSchoolId && schoolSubjects.items.length
      ? {
          label: '本校自命题科目',
          options: schoolSubjects.items.map((item) => ({
            value: item.id,
            label: subjectLabel(item, subjectSchoolId),
          })),
        }
      : null,
    examSubjectId !== undefined && !knownSubjectIds.has(examSubjectId)
      ? {
          label: '当前筛选',
          options: [{ value: examSubjectId, label: `科目 ${examSubjectId}` }],
        }
      : null,
  ].filter((group) => group !== null)

  return (
    <>
      <Space wrap style={{ margin: '16px 0' }}>
        <Input.Search
          allowClear
          placeholder="搜索名称"
          style={{ width: 240 }}
          value={draft.value}
          onChange={(event) => setDraft({ q, value: event.target.value })}
          onSearch={(value) => onChange({ q: value.trim() })}
        />
        <StatusFilterSelect
          value={status}
          onChange={(value) =>
            onChange({ status: value === 'all' ? null : value })
          }
        />
        <Select<AvailabilityStatus>
          allowClear
          placeholder="可授课状态"
          style={{ width: 140 }}
          value={availability}
          onChange={(value) => onChange({ availability: value ?? null })}
          options={AVAILABILITY_VALUES.map((value) => ({
            value,
            label: AVAILABILITY_LABEL[value],
          }))}
        />
        <Select<VerificationStatus>
          allowClear
          placeholder="核验状态"
          style={{ width: 140 }}
          value={verification}
          onChange={(value) => onChange({ verification: value ?? null })}
          options={VERIFICATION_VALUES.map((value) => ({
            value,
            label: VERIFICATION_LABEL[value],
          }))}
        />
        <Button onClick={() => setMoreOpen((open) => !open)}>更多筛选</Button>
      </Space>
      {moreOpen ? (
        <Space
          orientation="vertical"
          size="middle"
          style={{ marginBottom: 16 }}
        >
          <div>
            <Typography.Text strong>录取条件</Typography.Text>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
              院校、学院、专业、年份和学习方式需命中同一条当前有效录取记录。
            </Typography.Paragraph>
            <Space wrap>
              <Select
                showSearch
                allowClear
                placeholder="录取院校"
                optionFilterProp="label"
                style={{ width: 280 }}
                value={schoolId}
                onChange={(value: number | undefined) =>
                  onChange({
                    school_id: value ? String(value) : null,
                    college_id: null,
                    major_id: null,
                  })
                }
                options={schools.map((school) => ({
                  value: school.id,
                  label: entityLabel(
                    school.school_code,
                    school.name,
                    school.is_active,
                  ),
                }))}
              />
              <Select
                showSearch
                allowClear
                placeholder="学院"
                optionFilterProp="label"
                style={{ width: 220 }}
                value={collegeId}
                disabled={!schoolId}
                onChange={(value: number | undefined) =>
                  onChange({ college_id: value ? String(value) : null })
                }
                options={childLists.colleges.map((college) => ({
                  value: college.id,
                  label: entityLabel(
                    college.college_code,
                    college.name,
                    college.is_active,
                  ),
                }))}
              />
              <Select
                showSearch
                allowClear
                placeholder="专业"
                optionFilterProp="label"
                style={{ width: 220 }}
                value={majorId}
                disabled={!schoolId}
                onChange={(value: number | undefined) =>
                  onChange({ major_id: value ? String(value) : null })
                }
                options={childLists.majors.map((major) => ({
                  value: major.id,
                  label: entityLabel(
                    major.major_code,
                    major.name,
                    major.is_active,
                  ),
                }))}
              />
              <InputNumber
                min={2000}
                placeholder="录取年份"
                style={{ width: 140 }}
                value={admissionYear}
                onChange={(value) =>
                  onChange({
                    admission_year:
                      typeof value === 'number' ? String(value) : null,
                  })
                }
              />
              <Select<StudyMode>
                allowClear
                placeholder="学习方式"
                style={{ width: 140 }}
                value={studyMode}
                onChange={(value) => onChange({ study_mode: value ?? null })}
                options={(Object.keys(STUDY_MODE_LABEL) as StudyMode[]).map(
                  (value) => ({
                    value,
                    label: STUDY_MODE_LABEL[value],
                  }),
                )}
              />
            </Space>
          </div>
          <div>
            <Typography.Text strong>可教授科目</Typography.Text>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
              科目院校只用于加载该校自命题，不会作为录取院校筛选。
            </Typography.Paragraph>
            <Space wrap>
              <Select
                showSearch
                allowClear
                placeholder="科目院校"
                optionFilterProp="label"
                style={{ width: 280 }}
                value={subjectSchoolId}
                onChange={(value: number | undefined) =>
                  onChange({
                    subject_school_id: value ? String(value) : null,
                  })
                }
                options={schools.map((school) => ({
                  value: school.id,
                  label: entityLabel(
                    school.school_code,
                    school.name,
                    school.is_active,
                  ),
                }))}
              />
              <Select
                showSearch
                allowClear
                placeholder="选择科目"
                optionFilterProp="label"
                style={{ width: 320 }}
                value={examSubjectId}
                onChange={(value: number | undefined) =>
                  onChange({
                    exam_subject_id: value ? String(value) : null,
                  })
                }
                options={subjectGroups}
              />
            </Space>
          </div>
        </Space>
      ) : null}
    </>
  )
}
