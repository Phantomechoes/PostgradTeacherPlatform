import {
  Alert,
  App,
  Button,
  Descriptions,
  Result,
  Space,
  Typography,
} from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ApiError, isAbortError } from '../api/client'
import {
  createAdmissionRecord,
  getTeacherProfile,
  setAdmissionRecordStatus,
  setTeacherAvailability,
  setTeacherStatus,
  setTeacherVerification,
  replaceTeacherTeachSubjects,
  updateAdmissionRecord,
  updateTeacherProfile,
  type AdmissionRecordCreateBody,
  type AdmissionRecordPatch,
  type TeacherProfilePatch,
} from '../api/teacher'
import type {
  AdmissionRecordAdmin,
  AvailabilityStatus,
  TeacherAdminDetail,
  TeacherAdminSummary,
  VerificationStatus,
} from '../api/types'
import { AdmissionRecordsPanel } from '../features/teacher/AdmissionRecordsPanel'
import { upsertAdmissionRecord } from '../features/teacher/admissionRecordHelpers'
import { TeachSubjectsPanel } from '../features/teacher/TeachSubjectsPanel'
import { sortTeachSubjects } from '../features/teacher/teachSubjectHelpers'
import { mergeTeacherSummary } from '../features/teacher/mergeTeacherSummary'
import { TeacherProfileEditModal } from '../features/teacher/TeacherProfileEditModal'
import {
  TeacherStatusControls,
  type TeacherHeaderMutation,
} from '../features/teacher/TeacherStatusControls'
import { teacherErrorText } from '../features/teacher/teacherFormErrors'

export function TeacherDetailPage() {
  const { message } = App.useApp()
  const { teacherId } = useParams()
  const id = Number(teacherId)
  const validId = Number.isInteger(id) && id > 0
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${id}|${reloadKey}|${validId}`
  const [teacher, setTeacher] = useState<TeacherAdminDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [seenKey, setSeenKey] = useState(requestKey)
  const [headerSaving, setHeaderSaving] =
    useState<TeacherHeaderMutation | null>(null)
  const [editing, setEditing] = useState(false)
  const [admissionSaving, setAdmissionSaving] = useState<string | null>(null)
  const [teachSubjectSaving, setTeachSubjectSaving] = useState(false)
  const savingRef = useRef(false)
  const admissionLock = useRef(false)
  const teachSubjectLock = useRef(false)
  if (seenKey !== requestKey) {
    setSeenKey(requestKey)
    setLoading(true)
    setNotFound(false)
    setError(null)
    setTeacher(null)
    setEditing(false)
    setHeaderSaving(null)
    setAdmissionSaving(null)
    setTeachSubjectSaving(false)
  }

  useEffect(() => {
    if (!validId) {
      return
    }
    const controller = new AbortController()
    getTeacherProfile(id, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) {
          setTeacher(value)
        }
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError) || controller.signal.aborted) {
          return
        }
        setTeacher(null)
        if (
          loadError instanceof ApiError &&
          (loadError.status === 404 || loadError.code === 'not_found')
        ) {
          setNotFound(true)
          return
        }
        setError(teacherErrorText(loadError))
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [id, reloadKey, validId])

  async function runHeader(
    kind: TeacherHeaderMutation,
    action: () => Promise<TeacherAdminSummary>,
    successText: string,
  ): Promise<boolean> {
    if (savingRef.current) {
      return false
    }
    savingRef.current = true
    setHeaderSaving(kind)
    try {
      const summary = await action()
      setTeacher((current) =>
        current && current.id === summary.id
          ? mergeTeacherSummary(current, summary)
          : current,
      )
      message.success(successText)
      return true
    } finally {
      savingRef.current = false
      setHeaderSaving(null)
    }
  }

  async function saveProfile(patch: TeacherProfilePatch) {
    return runHeader(
      'profile',
      () => updateTeacherProfile(id, patch),
      '档案已保存',
    )
  }

  async function changeStatus(active: boolean) {
    try {
      await runHeader(
        'status',
        () => setTeacherStatus(id, active),
        active ? '师资已恢复' : '师资已停用',
      )
    } catch (statusError) {
      message.error(teacherErrorText(statusError))
    }
  }

  async function changeAvailability(value: AvailabilityStatus) {
    try {
      await runHeader(
        'availability',
        () => setTeacherAvailability(id, value),
        '可授课状态已更新',
      )
    } catch (availabilityError) {
      message.error(teacherErrorText(availabilityError))
    }
  }

  async function runAdmission(
    kind: string,
    action: () => Promise<AdmissionRecordAdmin>,
    successText: string,
  ): Promise<boolean> {
    if (admissionLock.current) {
      return false
    }
    admissionLock.current = true
    setAdmissionSaving(kind)
    try {
      const admission = await action()
      setTeacher((current) =>
        current && current.id === admission.teacher_profile_id
          ? upsertAdmissionRecord(current, admission)
          : current,
      )
      message.success(successText)
      return true
    } finally {
      admissionLock.current = false
      setAdmissionSaving(null)
    }
  }

  async function createAdmission(body: AdmissionRecordCreateBody) {
    return runAdmission(
      'create',
      () => createAdmissionRecord(id, body),
      '录取记录已创建',
    )
  }

  async function updateAdmission(
    admissionRecordId: number,
    patch: AdmissionRecordPatch,
  ) {
    return runAdmission(
      `edit:${admissionRecordId}`,
      () => updateAdmissionRecord(admissionRecordId, patch),
      '录取记录已保存',
    )
  }

  async function changeAdmissionStatus(
    admissionRecordId: number,
    active: boolean,
  ) {
    return runAdmission(
      `status:${admissionRecordId}`,
      () => setAdmissionRecordStatus(admissionRecordId, active),
      active ? '录取记录已恢复' : '录取记录已停用',
    )
  }

  async function saveTeachSubjects(examSubjectIds: number[]) {
    if (teachSubjectLock.current) {
      return false
    }
    teachSubjectLock.current = true
    setTeachSubjectSaving(true)
    try {
      const detail = await replaceTeacherTeachSubjects(id, examSubjectIds)
      setTeacher((current) =>
        current && current.id === detail.id
          ? {
              ...current,
              teach_subjects: sortTeachSubjects(detail.teach_subjects),
            }
          : current,
      )
      message.success('可教授科目已保存')
      return true
    } finally {
      teachSubjectLock.current = false
      setTeachSubjectSaving(false)
    }
  }

  async function changeVerification(value: VerificationStatus) {
    try {
      await runHeader(
        'verification',
        () => setTeacherVerification(id, value),
        '核验状态已更新',
      )
    } catch (verificationError) {
      message.error(teacherErrorText(verificationError))
    }
  }

  if (!validId || notFound) {
    return <Result status="404" title="未找到师资" />
  }
  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        message={error}
        action={
          <Button
            size="small"
            onClick={() => setReloadKey((value) => value + 1)}
          >
            重试
          </Button>
        }
      />
    )
  }
  if (loading || !teacher) {
    return <Typography.Paragraph>正在加载师资…</Typography.Paragraph>
  }

  const bio =
    teacher.bio === null || teacher.bio.trim() === '' ? null : teacher.bio

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>
          {teacher.display_name}
        </Typography.Title>
        <Button
          type="primary"
          disabled={headerSaving !== null}
          onClick={() => setEditing(true)}
        >
          编辑档案
        </Button>
      </div>
      <Typography.Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
        {bio === null ? (
          <Typography.Text type="secondary">暂无简介</Typography.Text>
        ) : (
          bio
        )}
      </Typography.Paragraph>
      <TeacherStatusControls
        active={teacher.is_active}
        availability={teacher.availability_status}
        verification={teacher.verification_status}
        saving={headerSaving}
        onStatus={(active) => {
          void changeStatus(active)
        }}
        onAvailability={(value) => {
          void changeAvailability(value)
        }}
        onVerification={(value) => {
          void changeVerification(value)
        }}
      />
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="录取记录数量">
          {teacher.admission_records.length}
        </Descriptions.Item>
        <Descriptions.Item label="可教授科目数量">
          {teacher.teach_subjects.length}
        </Descriptions.Item>
      </Descriptions>
      <AdmissionRecordsPanel
        teacherActive={teacher.is_active}
        records={teacher.admission_records}
        saving={admissionSaving}
        onCreate={createAdmission}
        onUpdate={updateAdmission}
        onStatus={changeAdmissionStatus}
      />
      <TeachSubjectsPanel
        teacherActive={teacher.is_active}
        subjects={teacher.teach_subjects}
        saving={teachSubjectSaving}
        onSave={saveTeachSubjects}
      />
      <TeacherProfileEditModal
        open={editing}
        displayName={teacher.display_name}
        bio={teacher.bio}
        onClose={() => setEditing(false)}
        onSubmit={saveProfile}
      />
    </Space>
  )
}
