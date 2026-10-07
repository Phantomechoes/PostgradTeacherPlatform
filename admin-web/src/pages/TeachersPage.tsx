import { Alert, App, Button, Table, Typography } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { isAbortError } from '../api/client'
import { createTeacher, listTeacherProfiles } from '../api/teacher'
import type {
  AvailabilityStatus,
  Page,
  StatusFilter,
  StudyMode,
  TeacherAdminSummary,
  VerificationStatus,
} from '../api/types'
import { StatusTag } from '../components/StatusTag'
import { TeacherCreateModal } from '../features/teacher/TeacherCreateModal'
import { TeacherFilters } from '../features/teacher/TeacherFilters'
import {
  AvailabilityTag,
  VerificationTag,
} from '../features/teacher/TeacherStatusTags'
import { teacherErrorText } from '../features/teacher/teacherFormErrors'

const PAGE_SIZE = 20

function isStatus(value: string | null): value is StatusFilter {
  return value === 'all' || value === 'active' || value === 'inactive'
}

function isAvailability(value: string | null): value is AvailabilityStatus {
  return value === 'unknown' || value === 'available' || value === 'unavailable'
}

function isVerification(value: string | null): value is VerificationStatus {
  return value === 'unverified' || value === 'verified' || value === 'rejected'
}

function isStudyMode(value: string | null): value is StudyMode {
  return value === 'full_time' || value === 'part_time'
}

function parsePositiveInt(value: string | null): number | undefined {
  if (value === null || value === '') {
    return undefined
  }
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

function parsePage(value: string | null): number {
  if (value === null) {
    return 1
  }
  const page = Number(value)
  return Number.isInteger(page) && page >= 1 ? page : 1
}

function parseYear(value: string | null): number | undefined {
  if (value === null || value === '') {
    return undefined
  }
  const year = Number(value)
  return Number.isInteger(year) && year >= 2000 ? year : undefined
}

function dropInvalid(next: URLSearchParams, key: string, valid: boolean) {
  if (next.get(key) !== null && !valid) {
    next.delete(key)
    return true
  }
  return false
}

export function TeachersPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const searchParamsRef = useRef(searchParams)
  const rawStatus = searchParams.get('status')
  const rawAvailability = searchParams.get('availability')
  const rawVerification = searchParams.get('verification')
  const rawMode = searchParams.get('study_mode')
  const rawPage = searchParams.get('page')
  const q = searchParams.get('q') ?? ''
  const status: StatusFilter =
    isStatus(rawStatus) || rawStatus === null ? (rawStatus ?? 'all') : 'all'
  const availability = isAvailability(rawAvailability)
    ? rawAvailability
    : undefined
  const verification = isVerification(rawVerification)
    ? rawVerification
    : undefined
  const schoolId = parsePositiveInt(searchParams.get('school_id'))
  const collegeId = parsePositiveInt(searchParams.get('college_id'))
  const majorId = parsePositiveInt(searchParams.get('major_id'))
  const admissionYear = parseYear(searchParams.get('admission_year'))
  const studyMode = isStudyMode(rawMode) ? rawMode : undefined
  const examSubjectId = parsePositiveInt(searchParams.get('exam_subject_id'))
  const subjectSchoolId = parsePositiveInt(
    searchParams.get('subject_school_id'),
  )
  const page = parsePage(rawPage)
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = [
    q,
    status,
    availability ?? '',
    verification ?? '',
    schoolId ?? '',
    collegeId ?? '',
    majorId ?? '',
    admissionYear ?? '',
    studyMode ?? '',
    examSubjectId ?? '',
    page,
    reloadKey,
  ].join('\n')
  const [request, setRequest] = useState<{
    key: string
    loading: boolean
    error: string | null
    result: Page<TeacherAdminSummary> | null
  }>({ key: requestKey, loading: true, error: null, result: null })
  if (request.key !== requestKey) {
    setRequest({
      key: requestKey,
      loading: true,
      error: null,
      result: request.result,
    })
  }
  const [createOpen, setCreateOpen] = useState(false)

  useEffect(() => {
    searchParamsRef.current = searchParams
  }, [searchParams])

  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    let changed = false
    changed = dropInvalid(next, 'status', isStatus(rawStatus)) || changed
    changed =
      dropInvalid(next, 'availability', isAvailability(rawAvailability)) ||
      changed
    changed =
      dropInvalid(next, 'verification', isVerification(rawVerification)) ||
      changed
    changed = dropInvalid(next, 'study_mode', isStudyMode(rawMode)) || changed
    for (const key of [
      'school_id',
      'college_id',
      'major_id',
      'exam_subject_id',
      'subject_school_id',
    ]) {
      if (
        next.get(key) !== null &&
        parsePositiveInt(next.get(key)) === undefined
      ) {
        next.delete(key)
        changed = true
      }
    }
    if (
      next.get('admission_year') !== null &&
      parseYear(next.get('admission_year')) === undefined
    ) {
      next.delete('admission_year')
      changed = true
    }
    if (searchParams.get('q') !== null && q.trim() === '') {
      next.delete('q')
      changed = true
    }
    if (rawPage !== null && parsePage(rawPage) === 1 && rawPage !== '1') {
      next.delete('page')
      changed = true
    }
    if (rawPage !== null && !/^[1-9]\d*$/.test(rawPage)) {
      next.delete('page')
      changed = true
    }
    if (changed) {
      setSearchParams(next, { replace: true })
    }
  }, [
    rawAvailability,
    rawMode,
    rawPage,
    rawStatus,
    q,
    rawVerification,
    searchParams,
    setSearchParams,
  ])

  useEffect(() => {
    const controller = new AbortController()
    listTeacherProfiles(
      {
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
        page,
        pageSize: PAGE_SIZE,
      },
      { signal: controller.signal },
    )
      .then((value) => {
        if (controller.signal.aborted) {
          return
        }
        setRequest((current) =>
          current.key === requestKey
            ? { ...current, loading: false, error: null, result: value }
            : current,
        )
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError) || controller.signal.aborted) {
          return
        }
        setRequest((current) =>
          current.key === requestKey
            ? {
                ...current,
                loading: false,
                error: teacherErrorText(loadError),
                result: null,
              }
            : current,
        )
      })
    return () => controller.abort()
  }, [
    admissionYear,
    availability,
    collegeId,
    examSubjectId,
    majorId,
    page,
    q,
    requestKey,
    schoolId,
    status,
    studyMode,
    verification,
  ])

  function replaceQuery(patch: Record<string, string | null>) {
    const next = new URLSearchParams(searchParamsRef.current)
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === '') {
        next.delete(key)
      } else {
        next.set(key, value)
      }
    }
    searchParamsRef.current = next
    setSearchParams(next)
  }

  const result = request.result
  const loading = request.loading
  const error = request.error

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>
          师资
        </Typography.Title>
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          新增师资
        </Button>
      </div>
      <TeacherFilters
        q={q}
        status={status}
        availability={availability}
        verification={verification}
        schoolId={schoolId}
        collegeId={collegeId}
        majorId={majorId}
        admissionYear={admissionYear}
        studyMode={studyMode}
        examSubjectId={examSubjectId}
        subjectSchoolId={subjectSchoolId}
        onChange={(patch) => replaceQuery({ ...patch, page: null })}
      />
      {error ? (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
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
      ) : null}
      <Table<TeacherAdminSummary>
        rowKey="id"
        loading={loading}
        dataSource={result?.items ?? []}
        locale={{ emptyText: loading || error ? ' ' : '暂无师资' }}
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: result?.total ?? 0,
          showSizeChanger: false,
          onChange: (nextPage) => {
            replaceQuery({ page: nextPage <= 1 ? null : String(nextPage) })
          },
        }}
        columns={[
          {
            title: '名称',
            dataIndex: 'display_name',
            ellipsis: true,
            render: (name: string, row) => (
              <Button
                type="link"
                style={{ paddingInline: 0 }}
                onClick={() => navigate(`/teachers/${row.id}`)}
              >
                {name}
              </Button>
            ),
          },
          {
            title: '档案状态',
            dataIndex: 'is_active',
            render: (active: boolean) => (
              <StatusTag mode="entity" active={active} />
            ),
          },
          {
            title: '可授课状态',
            dataIndex: 'availability_status',
            render: (value: AvailabilityStatus) => (
              <AvailabilityTag value={value} />
            ),
          },
          {
            title: '核验状态',
            dataIndex: 'verification_status',
            render: (value: VerificationStatus) => (
              <VerificationTag value={value} />
            ),
          },
        ]}
      />
      <TeacherCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={async (values) => {
          const created = await createTeacher(values)
          message.success('师资已创建')
          navigate(`/teachers/${created.id}`)
        }}
      />
    </>
  )
}
