import { Alert, Button, Descriptions, Result, Space, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ApiError, isAbortError } from '../api/client'
import { getTeacherProfile } from '../api/teacher'
import type { TeacherAdminDetail } from '../api/types'
import { StatusTag } from '../components/StatusTag'
import {
  AvailabilityTag,
  VerificationTag,
} from '../features/teacher/TeacherStatusTags'
import { teacherErrorText } from '../features/teacher/teacherFormErrors'

export function TeacherDetailPage() {
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
  if (seenKey !== requestKey) {
    setSeenKey(requestKey)
    setLoading(true)
    setNotFound(false)
    setError(null)
    setTeacher(null)
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
      <Typography.Title level={3} style={{ margin: 0 }}>
        {teacher.display_name}
      </Typography.Title>
      <Space wrap>
        <StatusTag mode="entity" active={teacher.is_active} />
        <AvailabilityTag value={teacher.availability_status} />
        <VerificationTag value={teacher.verification_status} />
      </Space>
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="简介">
          {bio === null ? (
            <Typography.Text type="secondary">暂无简介</Typography.Text>
          ) : (
            <Typography.Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {bio}
            </Typography.Paragraph>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="档案状态">
          <StatusTag mode="entity" active={teacher.is_active} />
        </Descriptions.Item>
        <Descriptions.Item label="可授课状态">
          <AvailabilityTag value={teacher.availability_status} />
        </Descriptions.Item>
        <Descriptions.Item label="核验状态">
          <VerificationTag value={teacher.verification_status} />
        </Descriptions.Item>
        <Descriptions.Item label="录取记录数量">
          {teacher.admission_records.length}
        </Descriptions.Item>
        <Descriptions.Item label="可教授科目数量">
          {teacher.teach_subjects.length}
        </Descriptions.Item>
      </Descriptions>
    </Space>
  )
}
