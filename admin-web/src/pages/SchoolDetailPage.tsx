import {
  Alert,
  App,
  Button,
  Result,
  Space,
  Table,
  Tabs,
  Tooltip,
  Typography,
} from 'antd'
import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { ApiError, isAbortError } from '../api/client'
import {
  createCollege,
  createMajor,
  createSchoolSubject,
  getSchool,
  listColleges,
  listMajors,
  listSchoolSubjects,
  setCollegeStatus,
  setMajorStatus,
  setSchoolStatus,
  setSubjectStatus,
  updateCollege,
  updateMajor,
  updateSchool,
  updateSubject,
} from '../api/masterData'
import type {
  CollegeAdmin,
  DegreeType,
  ExamSubjectAdmin,
  MajorAdmin,
  SchoolAdmin,
  StatusFilter,
} from '../api/types'
import { EntityStatusAction } from '../components/EntityStatusAction'
import { StatusFilterSelect } from '../components/StatusFilterSelect'
import { StatusTag } from '../components/StatusTag'
import {
  CollegeFormModal,
  MajorFormModal,
  SchoolFormModal,
  SubjectFormModal,
} from '../features/master-data/MasterDataForms'

type SchoolTab = 'colleges' | 'majors' | 'subjects'

function isSchoolTab(value: string | null): value is SchoolTab {
  return value === 'colleges' || value === 'majors' || value === 'subjects'
}

function degreeLabel(value: DegreeType): string {
  return value === 'academic' ? '学硕' : '专硕'
}

const INACTIVE_PARENT_HINT = '院校已停用，恢复院校后才能新增下级数据。'

function AddChildButton({
  disabled,
  onClick,
  children,
}: {
  disabled: boolean
  onClick: () => void
  children: string
}) {
  const button = (
    <Button type="primary" disabled={disabled} onClick={onClick}>
      {children}
    </Button>
  )
  if (!disabled) {
    return button
  }
  return (
    <Tooltip title={INACTIVE_PARENT_HINT}>
      <span title={INACTIVE_PARENT_HINT}>{button}</span>
    </Tooltip>
  )
}

export function SchoolDetailPage() {
  const { schoolId } = useParams()
  const id = Number(schoolId)
  const validId = Number.isInteger(id) && id > 0
  const [searchParams, setSearchParams] = useSearchParams()
  const raw = searchParams.get('tab')
  const active: SchoolTab = isSchoolTab(raw) ? raw : 'colleges'
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${id}|${reloadKey}|${validId}`
  const [school, setSchool] = useState<SchoolAdmin | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [seenKey, setSeenKey] = useState(requestKey)
  if (seenKey !== requestKey) {
    setSeenKey(requestKey)
    setLoading(true)
    setNotFound(false)
    setError(null)
    setSchool(null)
  }
  const [editing, setEditing] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)
  const { message } = App.useApp()

  useEffect(() => {
    if (raw !== null && !isSchoolTab(raw)) {
      setSearchParams({ tab: 'colleges' }, { replace: true })
    }
  }, [raw, setSearchParams])

  useEffect(() => {
    if (!validId) {
      return
    }
    const controller = new AbortController()
    getSchool(id, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) {
          setSchool(value)
        }
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError) || controller.signal.aborted) {
          return
        }
        setSchool(null)
        if (
          loadError instanceof ApiError &&
          (loadError.status === 404 || loadError.code === 'not_found')
        ) {
          setNotFound(true)
          return
        }
        setError(loadError instanceof ApiError ? loadError.message : '请求失败')
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [id, reloadKey, validId])

  async function changeSchoolStatus(next: boolean) {
    if (!school) {
      return
    }
    setStatusLoading(true)
    try {
      const updated = await setSchoolStatus(school.id, next)
      setSchool(updated)
    } catch (statusError) {
      message.error(
        statusError instanceof ApiError ? statusError.message : '请求失败',
      )
    } finally {
      setStatusLoading(false)
    }
  }

  if (!validId || notFound) {
    return <Result status="404" title="未找到院校" />
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
  if (loading || !school) {
    return <Typography.Paragraph>正在加载院校…</Typography.Paragraph>
  }

  return (
    <>
      <Space
        style={{ width: '100%', justifyContent: 'space-between' }}
        align="start"
      >
        <div>
          <Typography.Title level={3} style={{ marginBottom: 8 }}>
            {school.name}
          </Typography.Title>
          <Space>
            <Typography.Text>{school.school_code}</Typography.Text>
            <StatusTag mode="entity" active={school.is_active} />
          </Space>
        </div>
        <Space>
          <Button onClick={() => setEditing(true)}>编辑院校</Button>
          <EntityStatusAction
            active={school.is_active}
            loading={statusLoading}
            confirmTitle="确认停用该院校？"
            onChange={(next) => void changeSchoolStatus(next)}
          />
        </Space>
      </Space>
      <Tabs
        style={{ marginTop: 16 }}
        activeKey={active}
        onChange={(key) => setSearchParams({ tab: key })}
        items={[
          {
            key: 'colleges',
            label: '学院',
            children: (
              <CollegePanel
                schoolId={school.id}
                schoolActive={school.is_active}
                onParentInactive={() => setReloadKey((value) => value + 1)}
              />
            ),
          },
          {
            key: 'majors',
            label: '专业',
            children: (
              <MajorPanel
                schoolId={school.id}
                schoolActive={school.is_active}
                onParentInactive={() => setReloadKey((value) => value + 1)}
              />
            ),
          },
          {
            key: 'subjects',
            label: '自命题科目',
            children: (
              <SubjectPanel
                schoolId={school.id}
                schoolActive={school.is_active}
                onParentInactive={() => setReloadKey((value) => value + 1)}
              />
            ),
          },
        ]}
      />
      <SchoolFormModal
        open={editing}
        title="编辑院校"
        initial={{ school_code: school.school_code, name: school.name }}
        onClose={() => setEditing(false)}
        onSubmit={async (values) => {
          const updated = await updateSchool(school.id, values)
          setSchool(updated)
          message.success('院校已保存')
        }}
      />
    </>
  )
}

function ListAlert({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <Alert
      type="error"
      showIcon
      style={{ marginBottom: 16 }}
      message={message}
      action={
        <Button size="small" onClick={onRetry}>
          重试
        </Button>
      }
    />
  )
}

function CollegePanel({
  schoolId,
  schoolActive,
  onParentInactive,
}: {
  schoolId: number
  schoolActive: boolean
  onParentInactive: () => void
}) {
  const { message } = App.useApp()
  const [status, setStatus] = useState<StatusFilter>('all')
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${schoolId}|${status}|${reloadKey}`
  const [rows, setRows] = useState<CollegeAdmin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seenKey, setSeenKey] = useState(requestKey)
  if (seenKey !== requestKey) {
    setSeenKey(requestKey)
    setLoading(true)
    setError(null)
  }
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<CollegeAdmin | null>(null)
  const [statusId, setStatusId] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listColleges(schoolId, status, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) {
          setRows(value)
        }
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError) || controller.signal.aborted) {
          return
        }
        setRows([])
        setError(loadError instanceof ApiError ? loadError.message : '请求失败')
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [reloadKey, schoolId, status])

  async function changeStatus(row: CollegeAdmin, active: boolean) {
    setStatusId(row.id)
    try {
      await setCollegeStatus(row.id, active)
      setReloadKey((value) => value + 1)
    } catch (statusError) {
      message.error(
        statusError instanceof ApiError ? statusError.message : '请求失败',
      )
    } finally {
      setStatusId(null)
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <StatusFilterSelect value={status} onChange={setStatus} />
        <AddChildButton
          disabled={!schoolActive}
          onClick={() => setCreateOpen(true)}
        >
          新增学院
        </AddChildButton>
      </Space>
      {error ? (
        <ListAlert
          message={error}
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}
      <Table<CollegeAdmin>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: loading || error ? ' ' : '暂无学院' }}
        columns={[
          {
            title: '学院代码',
            dataIndex: 'college_code',
            render: (code: string | null) => code ?? '—',
          },
          { title: '学院名称', dataIndex: 'name' },
          {
            title: '状态',
            dataIndex: 'is_active',
            render: (active: boolean) => (
              <StatusTag mode="entity" active={active} />
            ),
          },
          {
            title: '操作',
            key: 'actions',
            render: (_, row) => (
              <Space size="small">
                <Button type="link" onClick={() => setEditing(row)}>
                  编辑
                </Button>
                <EntityStatusAction
                  active={row.is_active}
                  loading={statusId === row.id}
                  confirmTitle="确认停用该学院？"
                  onChange={(active) => void changeStatus(row, active)}
                />
              </Space>
            ),
          },
        ]}
      />
      <CollegeFormModal
        open={createOpen}
        title="新增学院"
        onClose={() => setCreateOpen(false)}
        onParentInactive={onParentInactive}
        onSubmit={async (values) => {
          await createCollege(schoolId, values)
          message.success('学院创建成功')
          setReloadKey((value) => value + 1)
        }}
      />
      <CollegeFormModal
        open={editing !== null}
        title="编辑学院"
        initial={
          editing
            ? { college_code: editing.college_code, name: editing.name }
            : undefined
        }
        onClose={() => setEditing(null)}
        onSubmit={async (values) => {
          if (!editing) {
            return
          }
          await updateCollege(editing.id, values)
          message.success('学院已保存')
          setReloadKey((value) => value + 1)
        }}
      />
    </>
  )
}

function MajorPanel({
  schoolId,
  schoolActive,
  onParentInactive,
}: {
  schoolId: number
  schoolActive: boolean
  onParentInactive: () => void
}) {
  const { message } = App.useApp()
  const [status, setStatus] = useState<StatusFilter>('all')
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${schoolId}|${status}|${reloadKey}`
  const [rows, setRows] = useState<MajorAdmin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seenKey, setSeenKey] = useState(requestKey)
  if (seenKey !== requestKey) {
    setSeenKey(requestKey)
    setLoading(true)
    setError(null)
  }
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<MajorAdmin | null>(null)
  const [statusId, setStatusId] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listMajors(schoolId, status, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) {
          setRows(value)
        }
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError) || controller.signal.aborted) {
          return
        }
        setRows([])
        setError(loadError instanceof ApiError ? loadError.message : '请求失败')
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [reloadKey, schoolId, status])

  async function changeStatus(row: MajorAdmin, active: boolean) {
    setStatusId(row.id)
    try {
      await setMajorStatus(row.id, active)
      setReloadKey((value) => value + 1)
    } catch (statusError) {
      message.error(
        statusError instanceof ApiError ? statusError.message : '请求失败',
      )
    } finally {
      setStatusId(null)
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <StatusFilterSelect value={status} onChange={setStatus} />
        <AddChildButton
          disabled={!schoolActive}
          onClick={() => setCreateOpen(true)}
        >
          新增专业
        </AddChildButton>
      </Space>
      {error ? (
        <ListAlert
          message={error}
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}
      <Table<MajorAdmin>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: loading || error ? ' ' : '暂无专业' }}
        columns={[
          { title: '专业代码', dataIndex: 'major_code' },
          { title: '专业名称', dataIndex: 'name' },
          {
            title: '类型',
            dataIndex: 'degree_type',
            render: (value: DegreeType) => degreeLabel(value),
          },
          {
            title: '状态',
            dataIndex: 'is_active',
            render: (active: boolean) => (
              <StatusTag mode="entity" active={active} />
            ),
          },
          {
            title: '操作',
            key: 'actions',
            render: (_, row) => (
              <Space size="small">
                <Button type="link" onClick={() => setEditing(row)}>
                  编辑
                </Button>
                <EntityStatusAction
                  active={row.is_active}
                  loading={statusId === row.id}
                  confirmTitle="确认停用该专业？"
                  onChange={(active) => void changeStatus(row, active)}
                />
              </Space>
            ),
          },
        ]}
      />
      <MajorFormModal
        open={createOpen}
        title="新增专业"
        onClose={() => setCreateOpen(false)}
        onParentInactive={onParentInactive}
        onSubmit={async (values) => {
          await createMajor(schoolId, values)
          message.success('专业创建成功')
          setReloadKey((value) => value + 1)
        }}
      />
      <MajorFormModal
        open={editing !== null}
        title="编辑专业"
        initial={
          editing
            ? {
                major_code: editing.major_code,
                name: editing.name,
                degree_type: editing.degree_type,
              }
            : undefined
        }
        onClose={() => setEditing(null)}
        onSubmit={async (values) => {
          if (!editing) {
            return
          }
          await updateMajor(editing.id, values)
          message.success('专业已保存')
          setReloadKey((value) => value + 1)
        }}
      />
    </>
  )
}

function SubjectPanel({
  schoolId,
  schoolActive,
  onParentInactive,
}: {
  schoolId: number
  schoolActive: boolean
  onParentInactive: () => void
}) {
  const { message } = App.useApp()
  const [status, setStatus] = useState<StatusFilter>('all')
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${schoolId}|${status}|${reloadKey}`
  const [rows, setRows] = useState<ExamSubjectAdmin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seenKey, setSeenKey] = useState(requestKey)
  if (seenKey !== requestKey) {
    setSeenKey(requestKey)
    setLoading(true)
    setError(null)
  }
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<ExamSubjectAdmin | null>(null)
  const [statusId, setStatusId] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listSchoolSubjects(schoolId, status, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) {
          setRows(value)
        }
      })
      .catch((loadError: unknown) => {
        if (isAbortError(loadError) || controller.signal.aborted) {
          return
        }
        setRows([])
        setError(loadError instanceof ApiError ? loadError.message : '请求失败')
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })
    return () => controller.abort()
  }, [reloadKey, schoolId, status])

  async function changeStatus(row: ExamSubjectAdmin, active: boolean) {
    setStatusId(row.id)
    try {
      await setSubjectStatus(row.id, active)
      setReloadKey((value) => value + 1)
    } catch (statusError) {
      message.error(
        statusError instanceof ApiError ? statusError.message : '请求失败',
      )
    } finally {
      setStatusId(null)
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <StatusFilterSelect value={status} onChange={setStatus} />
        <AddChildButton
          disabled={!schoolActive}
          onClick={() => setCreateOpen(true)}
        >
          新增自命题科目
        </AddChildButton>
      </Space>
      {error ? (
        <ListAlert
          message={error}
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}
      <Table<ExamSubjectAdmin>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: loading || error ? ' ' : '暂无科目' }}
        columns={[
          { title: '科目代码', dataIndex: 'subject_code' },
          { title: '科目名称', dataIndex: 'name' },
          {
            title: '状态',
            dataIndex: 'is_active',
            render: (active: boolean) => (
              <StatusTag mode="entity" active={active} />
            ),
          },
          {
            title: '操作',
            key: 'actions',
            render: (_, row) => (
              <Space size="small">
                <Button type="link" onClick={() => setEditing(row)}>
                  编辑
                </Button>
                <EntityStatusAction
                  active={row.is_active}
                  loading={statusId === row.id}
                  confirmTitle="确认停用该科目？"
                  onChange={(active) => void changeStatus(row, active)}
                />
              </Space>
            ),
          },
        ]}
      />
      <SubjectFormModal
        open={createOpen}
        title="新增自命题科目"
        onClose={() => setCreateOpen(false)}
        onParentInactive={onParentInactive}
        onSubmit={async (values) => {
          await createSchoolSubject(schoolId, values)
          message.success('科目创建成功')
          setReloadKey((value) => value + 1)
        }}
      />
      <SubjectFormModal
        open={editing !== null}
        title="编辑科目"
        initial={
          editing
            ? { subject_code: editing.subject_code, name: editing.name }
            : undefined
        }
        onClose={() => setEditing(null)}
        onSubmit={async (values) => {
          if (!editing) {
            return
          }
          await updateSubject(editing.id, values)
          message.success('科目已保存')
          setReloadKey((value) => value + 1)
        }}
      />
    </>
  )
}
