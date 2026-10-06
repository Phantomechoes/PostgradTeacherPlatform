import { App, Button, Space, Table, Typography } from 'antd'
import { useState } from 'react'
import type {
  AdmissionRecordCreateBody,
  AdmissionRecordPatch,
} from '../../api/teacher'
import type { AdmissionRecordAdmin, StudyMode } from '../../api/types'
import { EntityStatusAction } from '../../components/EntityStatusAction'
import { StatusTag } from '../../components/StatusTag'
import { STUDY_MODE_LABEL } from '../catalog/labels'
import { AdmissionRecordModal } from './AdmissionRecordModal'
import {
  collegeOptionLabel,
  formatScore,
  majorOptionLabel,
  schoolOptionLabel,
  sortAdmissionRecords,
} from './admissionRecordHelpers'
import { teacherErrorText } from './teacherFormErrors'

export function AdmissionRecordsPanel({
  teacherActive,
  records,
  saving,
  onCreate,
  onUpdate,
  onStatus,
}: {
  teacherActive: boolean
  records: AdmissionRecordAdmin[]
  saving: string | null
  onCreate: (body: AdmissionRecordCreateBody) => Promise<boolean>
  onUpdate: (id: number, patch: AdmissionRecordPatch) => Promise<boolean>
  onStatus: (id: number, active: boolean) => Promise<boolean>
}) {
  const { message } = App.useApp()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<AdmissionRecordAdmin | null>(null)
  const busy = saving !== null
  const rows = sortAdmissionRecords(records)

  async function changeStatus(record: AdmissionRecordAdmin, active: boolean) {
    try {
      await onStatus(record.id, active)
    } catch (error) {
      message.error(teacherErrorText(error))
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="page-toolbar">
        <Typography.Title level={4} style={{ margin: 0 }}>
          录取记录
        </Typography.Title>
        <Button
          type="primary"
          disabled={!teacherActive || busy}
          onClick={() => {
            if (!teacherActive || busy) {
              return
            }
            setEditing(null)
            setOpen(true)
          }}
        >
          新增录取
        </Button>
      </div>
      {teacherActive ? null : (
        <Typography.Text type="secondary">
          当前师资已停用，不能新增录取记录。
        </Typography.Text>
      )}
      <Table<AdmissionRecordAdmin>
        rowKey="id"
        dataSource={rows}
        pagination={false}
        scroll={{ x: 1400 }}
        locale={{ emptyText: '暂无录取记录' }}
        columns={[
          {
            title: '录取年份',
            dataIndex: 'admission_year',
            width: 110,
          },
          {
            title: '学习方式',
            dataIndex: 'study_mode',
            width: 110,
            render: (value: StudyMode) => STUDY_MODE_LABEL[value],
          },
          {
            title: '院校',
            width: 220,
            render: (_, record) => schoolOptionLabel(record.school),
          },
          {
            title: '学院',
            width: 200,
            render: (_, record) => collegeOptionLabel(record.college),
          },
          {
            title: '专业',
            width: 220,
            render: (_, record) => majorOptionLabel(record.major),
          },
          {
            title: '招生目录',
            width: 180,
            render: (_, record) =>
              record.admission_catalog_id === null
                ? '未关联'
                : `招生目录 #${record.admission_catalog_id}`,
          },
          {
            title: '初试总分',
            width: 110,
            render: (_, record) => formatScore(record.initial_total),
          },
          {
            title: '复试总分',
            width: 110,
            render: (_, record) => formatScore(record.retest_total),
          },
          {
            title: '最终总分',
            width: 110,
            render: (_, record) => formatScore(record.final_total),
          },
          {
            title: '状态',
            width: 90,
            render: (_, record) => (
              <StatusTag mode="entity" active={record.is_active} />
            ),
          },
          {
            title: '操作',
            width: 160,
            fixed: 'right',
            render: (_, record) => (
              <Space size="small">
                <Button
                  type="link"
                  disabled={busy}
                  onClick={() => {
                    setEditing(record)
                    setOpen(true)
                  }}
                >
                  编辑
                </Button>
                <EntityStatusAction
                  active={record.is_active}
                  loading={saving === `status:${record.id}`}
                  disabled={busy && saving !== `status:${record.id}`}
                  confirmTitle="确认停用该录取记录？"
                  description="停用不会删除历史录取数据。"
                  onChange={(active) => {
                    void changeStatus(record, active)
                  }}
                />
              </Space>
            ),
          },
        ]}
      />
      <AdmissionRecordModal
        open={open}
        record={editing}
        onClose={() => setOpen(false)}
        onCreate={onCreate}
        onUpdate={onUpdate}
      />
    </Space>
  )
}
