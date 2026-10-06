import {
  App,
  Button,
  Card,
  Checkbox,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd'
import { useEffect, useRef, useState } from 'react'
import { isAbortError } from '../../api/client'
import {
  listAllSchools,
  listNationalSubjects,
  listSchoolSubjects,
} from '../../api/masterData'
import type { ExamSubjectAdmin, SchoolAdmin } from '../../api/types'
import { entityLabel } from '../catalog/labels'
import {
  addedTeachSubjectIds,
  sameTeachSubjectIds,
  sortTeachSubjects,
  teachSubjectIds,
  teachSubjectKind,
} from './teachSubjectHelpers'
import { teacherErrorText } from './teacherFormErrors'

function SubjectLine({ subject }: { subject: ExamSubjectAdmin }) {
  return (
    <Space size="small" wrap>
      <span>
        {subject.subject_code} {subject.name}
      </span>
      <Tag>{teachSubjectKind(subject)}</Tag>
      {subject.is_active ? <Tag color="green">启用</Tag> : <Tag>已停用</Tag>}
    </Space>
  )
}

export function TeachSubjectsEditor({
  baseline,
  teacherActive,
  saving,
  onClose,
  onSave,
}: {
  baseline: ExamSubjectAdmin[]
  teacherActive: boolean
  saving: boolean
  onClose: () => void
  onSave: (examSubjectIds: number[]) => Promise<boolean>
}) {
  const { message } = App.useApp()
  const savingRef = useRef(false)
  const baselineIds = teachSubjectIds(baseline.map((subject) => subject.id))
  const [draftIds, setDraftIds] = useState<number[]>(baselineIds)
  const [addedSubjects, setAddedSubjects] = useState<ExamSubjectAdmin[]>([])
  const [national, setNational] = useState<ExamSubjectAdmin[] | null>(null)
  const [schools, setSchools] = useState<SchoolAdmin[] | null>(null)
  const [subjectSchoolId, setSubjectSchoolId] = useState<number | undefined>()
  const [schoolSubjects, setSchoolSubjects] = useState<ExamSubjectAdmin[]>([])
  const [loadedSchoolId, setLoadedSchoolId] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listNationalSubjects('active', { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) {
          setNational(sortTeachSubjects(items))
        }
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) {
          return
        }
        setNational([])
        message.error(teacherErrorText(error))
      })
    return () => controller.abort()
  }, [message])

  useEffect(() => {
    const controller = new AbortController()
    listAllSchools('all', { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) {
          setSchools([...items].sort((left, right) => left.id - right.id))
        }
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) {
          return
        }
        setSchools([])
        message.error(teacherErrorText(error))
      })
    return () => controller.abort()
  }, [message])

  useEffect(() => {
    if (typeof subjectSchoolId !== 'number') {
      return
    }
    const requestedSchoolId = subjectSchoolId
    const controller = new AbortController()
    listSchoolSubjects(requestedSchoolId, 'active', {
      signal: controller.signal,
    })
      .then((items) => {
        if (controller.signal.aborted) {
          return
        }
        setSchoolSubjects(sortTeachSubjects(items))
        setLoadedSchoolId(requestedSchoolId)
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) {
          return
        }
        setSchoolSubjects([])
        setLoadedSchoolId(requestedSchoolId)
        message.error(teacherErrorText(error))
      })
    return () => controller.abort()
  }, [message, subjectSchoolId])

  const requestedIds = teachSubjectIds(draftIds)
  const addedIds = addedTeachSubjectIds(baselineIds, requestedIds)
  const visibleAdded = sortTeachSubjects(
    addedSubjects.filter((subject) => addedIds.includes(subject.id)),
  )
  const nationalLoading = national === null
  const schoolsLoading = schools === null
  const schoolSubjectsLoading =
    typeof subjectSchoolId === 'number' && loadedSchoolId !== subjectSchoolId
  const visibleSchoolSubjects =
    loadedSchoolId === subjectSchoolId ? schoolSubjects : []
  const nationalCandidates = (national ?? []).filter(
    (subject) => !requestedIds.includes(subject.id),
  )
  const schoolCandidates = visibleSchoolSubjects.filter(
    (subject) => !requestedIds.includes(subject.id),
  )

  function setRetained(subjectId: number, retained: boolean) {
    setDraftIds((current) =>
      teachSubjectIds(
        retained
          ? [...current, subjectId]
          : current.filter((id) => id !== subjectId),
      ),
    )
  }

  function addCandidate(subject: ExamSubjectAdmin) {
    if (!teacherActive || requestedIds.includes(subject.id)) {
      return
    }
    setAddedSubjects((current) =>
      current.some((item) => item.id === subject.id)
        ? current
        : [...current, subject],
    )
    setDraftIds((current) => teachSubjectIds([...current, subject.id]))
  }

  function removeAdded(subjectId: number) {
    setDraftIds((current) => current.filter((id) => id !== subjectId))
  }

  async function submit() {
    if (savingRef.current || saving) {
      return
    }
    if (!teacherActive && addedIds.length > 0) {
      message.error('当前师资已停用，请移除本次新增科目后再保存。')
      return
    }
    if (sameTeachSubjectIds(requestedIds, baselineIds)) {
      message.info('没有修改')
      onClose()
      return
    }
    savingRef.current = true
    try {
      const saved = await onSave(requestedIds)
      if (saved) {
        onClose()
      }
    } catch (error) {
      message.error(teacherErrorText(error))
    } finally {
      savingRef.current = false
    }
  }

  return (
    <Card title="编辑可教授科目">
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
        <div>
          <Typography.Title level={5}>当前已有关系</Typography.Title>
          {baseline.length === 0 ? (
            <Typography.Text type="secondary">暂无已有科目</Typography.Text>
          ) : (
            <Space orientation="vertical" size="small">
              {baseline.map((subject) => (
                <Checkbox
                  key={subject.id}
                  checked={requestedIds.includes(subject.id)}
                  onChange={(event) =>
                    setRetained(subject.id, event.target.checked)
                  }
                >
                  <SubjectLine subject={subject} />
                </Checkbox>
              ))}
            </Space>
          )}
        </div>
        {visibleAdded.length > 0 ? (
          <div>
            <Typography.Title level={5}>本次新增</Typography.Title>
            {!teacherActive ? (
              <Typography.Paragraph type="secondary">
                当前师资已停用，请移除本次新增科目后再保存。
              </Typography.Paragraph>
            ) : null}
            <Space orientation="vertical" size="small">
              {visibleAdded.map((subject) => (
                <Space key={subject.id} size="small">
                  <SubjectLine subject={subject} />
                  <Button
                    type="link"
                    disabled={saving}
                    onClick={() => removeAdded(subject.id)}
                  >
                    移除
                  </Button>
                </Space>
              ))}
            </Space>
          </div>
        ) : null}
        <div>
          <Typography.Title level={5}>可新增科目</Typography.Title>
          {teacherActive ? (
            <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
              科目所属院校只用于加载该校自命题，与录取院校无关。
            </Typography.Paragraph>
          ) : (
            <Typography.Paragraph type="secondary">
              当前师资已停用，只能保留或移除已有可教授科目，不能新增。
            </Typography.Paragraph>
          )}
          <Space orientation="vertical" size="small" style={{ width: '100%' }}>
            <Typography.Text>全国统考</Typography.Text>
            {nationalLoading ? (
              <Typography.Text type="secondary">正在加载科目…</Typography.Text>
            ) : null}
            <div style={{ maxHeight: 220, overflow: 'auto' }}>
              <Space orientation="vertical" size="small">
                {nationalCandidates.map((subject) => (
                  <Button
                    key={subject.id}
                    disabled={!teacherActive || saving}
                    onClick={() => addCandidate(subject)}
                  >
                    添加 {subject.subject_code} {subject.name}
                  </Button>
                ))}
              </Space>
            </div>
            <Typography.Text>学校自命题</Typography.Text>
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              placeholder="科目所属院校"
              style={{ width: '100%' }}
              loading={schoolsLoading}
              disabled={!teacherActive || saving}
              value={subjectSchoolId}
              onChange={(value: number | undefined) =>
                setSubjectSchoolId(value)
              }
              options={(schools ?? []).map((school) => ({
                value: school.id,
                label: entityLabel(
                  school.school_code,
                  school.name,
                  school.is_active,
                ),
              }))}
            />
            {typeof subjectSchoolId !== 'number' ? (
              <Typography.Text type="secondary">
                请先选择科目所属院校
              </Typography.Text>
            ) : null}
            {schoolSubjectsLoading ? (
              <Typography.Text type="secondary">正在加载科目…</Typography.Text>
            ) : null}
            <div style={{ maxHeight: 220, overflow: 'auto' }}>
              <Space orientation="vertical" size="small">
                {schoolCandidates.map((subject) => (
                  <Button
                    key={subject.id}
                    disabled={!teacherActive || saving}
                    onClick={() => addCandidate(subject)}
                  >
                    添加 {subject.subject_code} {subject.name}
                  </Button>
                ))}
              </Space>
            </div>
          </Space>
        </div>
        <Space>
          <Button
            type="primary"
            loading={saving}
            onClick={() => {
              void submit()
            }}
          >
            保存
          </Button>
          <Button disabled={saving} onClick={onClose}>
            取消
          </Button>
        </Space>
      </Space>
    </Card>
  )
}
