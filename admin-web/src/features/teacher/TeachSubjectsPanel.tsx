import { Button, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import type { ExamSubjectAdmin } from '../../api/types'
import { TeachSubjectsEditor } from './TeachSubjectsEditor'
import { sortTeachSubjects, teachSubjectKind } from './teachSubjectHelpers'

export function TeachSubjectsPanel({
  teacherActive,
  subjects,
  saving,
  onSave,
}: {
  teacherActive: boolean
  subjects: ExamSubjectAdmin[]
  saving: boolean
  onSave: (examSubjectIds: number[]) => Promise<boolean>
}) {
  const [open, setOpen] = useState(false)
  const [baseline, setBaseline] = useState<ExamSubjectAdmin[]>([])
  const rows = sortTeachSubjects(subjects)

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="page-toolbar">
        <Typography.Title level={4} style={{ margin: 0 }}>
          可教授科目
        </Typography.Title>
        <Button
          type="primary"
          disabled={saving}
          onClick={() => {
            setBaseline(sortTeachSubjects(subjects))
            setOpen(true)
          }}
        >
          编辑科目
        </Button>
      </div>
      <Table<ExamSubjectAdmin>
        rowKey="id"
        dataSource={rows}
        pagination={false}
        scroll={{ x: 760 }}
        locale={{ emptyText: '暂无可教授科目' }}
        columns={[
          {
            title: '科目代码',
            dataIndex: 'subject_code',
            width: 160,
          },
          {
            title: '名称',
            dataIndex: 'name',
          },
          {
            title: '类型',
            width: 140,
            render: (_, subject) => teachSubjectKind(subject),
          },
          {
            title: '状态',
            width: 110,
            render: (_, subject) =>
              subject.is_active ? (
                <Tag color="green">启用</Tag>
              ) : (
                <Tag>已停用</Tag>
              ),
          },
        ]}
      />
      {open ? (
        <TeachSubjectsEditor
          key={baseline.map((subject) => subject.id).join(',') || 'empty'}
          baseline={baseline}
          teacherActive={teacherActive}
          saving={saving}
          onClose={() => setOpen(false)}
          onSave={onSave}
        />
      ) : null}
    </Space>
  )
}
