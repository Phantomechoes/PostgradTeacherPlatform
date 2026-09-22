import {
  Alert,
  App,
  Button,
  InputNumber,
  Select,
  Space,
  Table,
  Typography,
} from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { createCatalogShell, listCatalogs } from '../api/catalog'
import { ApiError, isAbortError } from '../api/client'
import { listAllSchools, listColleges, listMajors } from '../api/masterData'
import type {
  CatalogAdminSummary,
  CollegeAdmin,
  MajorAdmin,
  Page,
  SchoolAdmin,
  StatusFilter,
  StudyMode,
} from '../api/types'
import { StatusTag } from '../components/StatusTag'
import { CatalogShellModal } from '../features/catalog/CatalogShellModal'
import { entityLabel, STUDY_MODE_LABEL } from '../features/catalog/labels'

const PAGE_SIZE = 20

function isStatus(value: string | null): value is StatusFilter {
  return value === 'all' || value === 'active' || value === 'inactive'
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

export function CatalogsPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const searchParamsRef = useRef(searchParams)
  const schoolId = parsePositiveInt(searchParams.get('school_id'))
  const rawStatus = searchParams.get('status')
  const status: StatusFilter =
    isStatus(rawStatus) || rawStatus === null ? (rawStatus ?? 'all') : 'all'
  const admissionYear = parseYear(searchParams.get('admission_year'))
  const collegeId = parsePositiveInt(searchParams.get('college_id'))
  const majorId = parsePositiveInt(searchParams.get('major_id'))
  const rawMode = searchParams.get('study_mode')
  const studyMode = isStudyMode(rawMode) ? rawMode : undefined
  const rawPage = searchParams.get('page')
  const page = parsePage(rawPage)
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = [
    schoolId ?? '',
    status,
    admissionYear ?? '',
    collegeId ?? '',
    majorId ?? '',
    studyMode ?? '',
    page,
    reloadKey,
  ].join('|')
  const [request, setRequest] = useState<{
    key: string
    loading: boolean
    error: string | null
    result: Page<CatalogAdminSummary> | null
  }>({
    key: requestKey,
    loading: Boolean(schoolId),
    error: null,
    result: null,
  })
  if (request.key !== requestKey) {
    setRequest({
      key: requestKey,
      loading: Boolean(schoolId),
      error: null,
      result: schoolId ? request.result : null,
    })
  }
  const [schools, setSchools] = useState<SchoolAdmin[]>([])
  const childKey = schoolId ?? 0
  const [childLists, setChildLists] = useState<{
    key: number
    colleges: CollegeAdmin[]
    majors: MajorAdmin[]
  }>({ key: childKey, colleges: [], majors: [] })
  if (childLists.key !== childKey) {
    setChildLists({ key: childKey, colleges: [], majors: [] })
  }
  const colleges = childLists.colleges
  const majors = childLists.majors
  const [createOpen, setCreateOpen] = useState(false)

  useEffect(() => {
    searchParamsRef.current = searchParams
  }, [searchParams])

  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    let changed = false
    if (rawStatus !== null && !isStatus(rawStatus)) {
      next.delete('status')
      changed = true
    }
    if (rawMode !== null && !isStudyMode(rawMode)) {
      next.delete('study_mode')
      changed = true
    }
    if (
      rawPage !== null &&
      (parsePage(rawPage) === 1 || !/^[1-9]\d*$/.test(rawPage))
    ) {
      next.delete('page')
      changed = true
    }
    if (searchParams.get('school_id') && !schoolId) {
      next.delete('school_id')
      changed = true
    }
    if (changed) {
      setSearchParams(next, { replace: true })
    }
  }, [rawMode, rawPage, rawStatus, schoolId, searchParams, setSearchParams])

  useEffect(() => {
    const controller = new AbortController()
    listAllSchools('all', { signal: controller.signal })
      .then(setSchools)
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
    if (!schoolId) {
      return
    }
    const controller = new AbortController()
    const key = schoolId
    Promise.all([
      listColleges(schoolId, 'all', { signal: controller.signal }),
      listMajors(schoolId, 'all', { signal: controller.signal }),
    ])
      .then(([nextColleges, nextMajors]) => {
        setChildLists((current) =>
          current.key === key
            ? { key, colleges: nextColleges, majors: nextMajors }
            : current,
        )
      })
      .catch((error: unknown) => {
        if (!isAbortError(error) && !controller.signal.aborted) {
          setChildLists((current) =>
            current.key === key ? { key, colleges: [], majors: [] } : current,
          )
        }
      })
    return () => controller.abort()
  }, [schoolId])

  useEffect(() => {
    if (!schoolId) {
      return
    }
    const controller = new AbortController()
    listCatalogs(
      {
        schoolId,
        status,
        admissionYear,
        collegeId,
        majorId,
        studyMode,
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
        const messageText =
          loadError instanceof ApiError ? loadError.message : '请求失败'
        setRequest((current) =>
          current.key === requestKey
            ? { ...current, loading: false, error: messageText, result: null }
            : current,
        )
      })
    return () => controller.abort()
  }, [
    admissionYear,
    collegeId,
    majorId,
    page,
    requestKey,
    schoolId,
    status,
    studyMode,
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

  function changeSchool(nextId: number | undefined) {
    replaceQuery({
      school_id: nextId ? String(nextId) : null,
      college_id: null,
      major_id: null,
      page: null,
    })
  }

  const result = request.result
  const loading = request.loading
  const error = request.error

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>
          招生目录
        </Typography.Title>
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          新增招生目录
        </Button>
      </div>
      <Space wrap style={{ margin: '16px 0' }}>
        <Select
          showSearch
          allowClear
          placeholder="选择院校"
          optionFilterProp="label"
          style={{ width: 280 }}
          value={schoolId}
          onChange={(value) => changeSchool(value)}
          options={schools.map((school) => ({
            value: school.id,
            label: entityLabel(
              school.school_code,
              school.name,
              school.is_active,
            ),
          }))}
        />
        <Select<StatusFilter>
          value={status}
          style={{ width: 140 }}
          onChange={(value) =>
            replaceQuery({
              status: value === 'all' ? null : value,
              page: null,
            })
          }
          options={[
            { value: 'all', label: '全部' },
            { value: 'active', label: '已公开' },
            { value: 'inactive', label: '未公开' },
          ]}
        />
        <InputNumber
          min={2000}
          placeholder="招生年份"
          style={{ width: 140 }}
          value={admissionYear}
          onChange={(value) =>
            replaceQuery({
              admission_year: typeof value === 'number' ? String(value) : null,
              page: null,
            })
          }
        />
        <Select
          allowClear
          placeholder="学院"
          optionFilterProp="label"
          style={{ width: 220 }}
          value={collegeId}
          disabled={!schoolId}
          onChange={(value) =>
            replaceQuery({
              college_id: value ? String(value) : null,
              page: null,
            })
          }
          options={colleges.map((college) => ({
            value: college.id,
            label: entityLabel(
              college.college_code,
              college.name,
              college.is_active,
            ),
          }))}
        />
        <Select
          allowClear
          placeholder="专业"
          optionFilterProp="label"
          style={{ width: 220 }}
          value={majorId}
          disabled={!schoolId}
          onChange={(value) =>
            replaceQuery({
              major_id: value ? String(value) : null,
              page: null,
            })
          }
          options={majors.map((major) => ({
            value: major.id,
            label: entityLabel(major.major_code, major.name, major.is_active),
          }))}
        />
        <Select
          allowClear
          placeholder="学习方式"
          style={{ width: 140 }}
          value={studyMode}
          onChange={(value) =>
            replaceQuery({
              study_mode: value ?? null,
              page: null,
            })
          }
          options={(Object.keys(STUDY_MODE_LABEL) as StudyMode[]).map(
            (value) => ({
              value,
              label: STUDY_MODE_LABEL[value],
            }),
          )}
        />
      </Space>
      {!schoolId ? (
        <Alert
          type="info"
          showIcon
          message="请先选择院校，才能查看招生目录。"
        />
      ) : error ? (
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
      ) : (
        <Table<CatalogAdminSummary>
          rowKey="id"
          loading={loading}
          dataSource={result?.items ?? []}
          locale={{ emptyText: loading ? ' ' : '暂无招生目录' }}
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
              title: '年份',
              dataIndex: 'admission_year',
            },
            {
              title: '学习方式',
              dataIndex: 'study_mode',
              render: (value: StudyMode) => STUDY_MODE_LABEL[value],
            },
            {
              title: '学院',
              ellipsis: true,
              render: (_, row) =>
                entityLabel(
                  row.college.college_code,
                  row.college.name,
                  row.college.is_active,
                ),
            },
            {
              title: '专业',
              ellipsis: true,
              render: (_, row) =>
                entityLabel(
                  row.major.major_code,
                  row.major.name,
                  row.major.is_active,
                ),
            },
            {
              title: '状态',
              dataIndex: 'is_active',
              render: (active: boolean) => (
                <StatusTag mode="catalog" active={active} />
              ),
            },
            {
              title: '操作',
              key: 'actions',
              render: (_, row) => (
                <Button
                  type="link"
                  onClick={() => navigate(`/catalogs/${row.id}`)}
                >
                  编辑
                </Button>
              ),
            },
          ]}
        />
      )}
      <CatalogShellModal
        open={createOpen}
        schools={schools}
        defaultSchoolId={schoolId}
        onClose={() => setCreateOpen(false)}
        onSubmit={async (values) => {
          const created = await createCatalogShell(values)
          message.success('已创建未公开的招生目录')
          navigate(`/catalogs/${created.id}`)
        }}
      />
    </>
  )
}
