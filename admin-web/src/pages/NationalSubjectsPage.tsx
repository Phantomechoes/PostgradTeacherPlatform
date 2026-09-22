import { Alert, App, Button, Space, Table, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError, isAbortError } from '../api/client'
import {
  createNationalSubject,
  listNationalSubjects,
  setSubjectStatus,
  updateSubject,
} from '../api/masterData'
import type { ExamSubjectAdmin, StatusFilter } from '../api/types'
import { EntityStatusAction } from '../components/EntityStatusAction'
import { StatusFilterSelect } from '../components/StatusFilterSelect'
import { StatusTag } from '../components/StatusTag'
import { SubjectFormModal } from '../features/master-data/MasterDataForms'

export function NationalSubjectsPage() {
  const { message } = App.useApp()
  const [status, setStatus] = useState<StatusFilter>('all')
  const [reloadKey, setReloadKey] = useState(0)
  const requestKey = `${status}\n${reloadKey}`
  const [request, setRequest] = useState<{
    key: string
    loading: boolean
    error: string | null
    rows: ExamSubjectAdmin[]
  }>({ key: requestKey, loading: true, error: null, rows: [] })
  if (request.key !== requestKey) {
    setRequest({
      key: requestKey,
      loading: true,
      error: null,
      rows: request.rows,
    })
  }
  const rows = request.rows
  const loading = request.loading
  const error = request.error
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<ExamSubjectAdmin | null>(null)
  const [statusId, setStatusId] = useState<number | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listNationalSubjects(status, { signal: controller.signal })
      .then((value) => {
        if (controller.signal.aborted) {
          return
        }
        setRequest((current) =>
          current.key === requestKey
            ? { ...current, loading: false, error: null, rows: value }
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
            ? { ...current, loading: false, error: messageText, rows: [] }
            : current,
        )
      })
    return () => controller.abort()
  }, [requestKey, status])

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
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>
          全国统考科目
        </Typography.Title>
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          新增科目
        </Button>
      </div>
      <div style={{ margin: '16px 0' }}>
        <StatusFilterSelect value={status} onChange={setStatus} />
      </div>
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
        title="新增全国统考科目"
        onClose={() => setCreateOpen(false)}
        onSubmit={async (values) => {
          await createNationalSubject(values)
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
