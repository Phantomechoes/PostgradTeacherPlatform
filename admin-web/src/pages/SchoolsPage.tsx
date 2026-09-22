import { Alert, App, Button, Input, Space, Table, Typography } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, isAbortError } from '../api/client'
import {
  createSchool,
  listSchools,
  setSchoolStatus,
  updateSchool,
} from '../api/masterData'
import type { Page, SchoolAdmin, StatusFilter } from '../api/types'
import { EntityStatusAction } from '../components/EntityStatusAction'
import { StatusFilterSelect } from '../components/StatusFilterSelect'
import { StatusTag } from '../components/StatusTag'
import { SchoolFormModal } from '../features/master-data/MasterDataForms'

const PAGE_SIZE = 20

function isStatus(value: string | null): value is StatusFilter {
  return value === 'all' || value === 'active' || value === 'inactive'
}

function parsePage(value: string | null): number {
  if (value === null) {
    return 1
  }
  const page = Number(value)
  return Number.isInteger(page) && page >= 1 ? page : 1
}

export function SchoolsPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const searchParamsRef = useRef(searchParams)
  const rawStatus = searchParams.get('status')
  const rawPage = searchParams.get('page')
  const q = searchParams.get('q') ?? ''
  const status: StatusFilter =
    isStatus(rawStatus) || rawStatus === null ? (rawStatus ?? 'all') : 'all'
  const page = parsePage(rawPage)
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${q}\n${status}\n${page}\n${reloadKey}`
  const [draft, setDraft] = useState({ q, value: q })
  const [request, setRequest] = useState<{
    key: string
    loading: boolean
    error: string | null
    result: Page<SchoolAdmin> | null
  }>({ key: requestKey, loading: true, error: null, result: null })
  if (draft.q !== q) {
    setDraft({ q, value: q })
  }
  if (request.key !== requestKey) {
    setRequest({
      key: requestKey,
      loading: true,
      error: null,
      result: request.result,
    })
  }
  const draftQ = draft.value
  const result = request.result
  const loading = request.loading
  const error = request.error
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<SchoolAdmin | null>(null)
  const [statusId, setStatusId] = useState<number | null>(null)

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
  }, [rawPage, rawStatus, searchParams, setSearchParams])

  useEffect(() => {
    const controller = new AbortController()
    listSchools(
      { q, status, page, pageSize: PAGE_SIZE },
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
  }, [page, q, requestKey, status])

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

  async function changeStatus(row: SchoolAdmin, active: boolean) {
    setStatusId(row.id)
    try {
      await setSchoolStatus(row.id, active)
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
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>
          院校
        </Typography.Title>
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          新增院校
        </Button>
      </div>
      <Space style={{ margin: '16px 0' }}>
        <Input.Search
          allowClear
          placeholder="搜索院校代码或名称"
          style={{ width: 280 }}
          value={draftQ}
          onChange={(event) => setDraft({ q, value: event.target.value })}
          onSearch={(value) => {
            replaceQuery({ q: value.trim(), page: null })
          }}
        />
        <StatusFilterSelect
          value={status}
          onChange={(value) => {
            replaceQuery({
              status: value === 'all' ? null : value,
              page: null,
            })
          }}
        />
      </Space>
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
      <Table<SchoolAdmin>
        rowKey="id"
        loading={loading}
        dataSource={result?.items ?? []}
        locale={{ emptyText: loading || error ? ' ' : '暂无院校' }}
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
          { title: '院校代码', dataIndex: 'school_code', ellipsis: true },
          { title: '院校名称', dataIndex: 'name', ellipsis: true },
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
                <Button
                  type="link"
                  onClick={() => navigate(`/schools/${row.id}`)}
                >
                  查看
                </Button>
                <Button type="link" onClick={() => setEditing(row)}>
                  编辑
                </Button>
                <EntityStatusAction
                  active={row.is_active}
                  loading={statusId === row.id}
                  confirmTitle="确认停用该院校？"
                  onChange={(active) => void changeStatus(row, active)}
                />
              </Space>
            ),
          },
        ]}
      />
      <SchoolFormModal
        open={createOpen}
        title="新增院校"
        onClose={() => setCreateOpen(false)}
        onSubmit={async (values) => {
          await createSchool(values)
          message.success('院校创建成功')
          setReloadKey((value) => value + 1)
        }}
      />
      <SchoolFormModal
        open={editing !== null}
        title="编辑院校"
        initial={
          editing
            ? { school_code: editing.school_code, name: editing.name }
            : undefined
        }
        onClose={() => setEditing(null)}
        onSubmit={async (values) => {
          if (!editing) {
            return
          }
          await updateSchool(editing.id, values)
          message.success('院校已保存')
          setReloadKey((value) => value + 1)
        }}
      />
    </>
  )
}
