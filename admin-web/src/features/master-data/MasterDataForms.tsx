import { App, Form, Input, Modal, Select } from 'antd'
import { useState } from 'react'
import { mapApiError } from '../../api/formErrors'
import type { DegreeType } from '../../api/types'

const PARENT_INACTIVE_MESSAGE = '院校已停用，无法新增下级数据。'

type SchoolValues = { school_code: string; name: string }
type MajorValues = { major_code: string; name: string; degree_type: DegreeType }
type SubjectValues = { subject_code: string; name: string }

function trim(value: string | undefined): string {
  return value?.trim() ?? ''
}

export function SchoolFormModal({
  open,
  title,
  initial,
  onClose,
  onSubmit,
}: {
  open: boolean
  title: string
  initial?: SchoolValues
  onClose: () => void
  onSubmit: (values: SchoolValues) => Promise<void>
}) {
  return (
    <TextFormModal
      open={open}
      title={title}
      initial={initial ?? { school_code: '', name: '' }}
      fields={[
        {
          name: 'school_code',
          label: '院校代码',
          max: 32,
          required: '请输入院校代码',
        },
        {
          name: 'name',
          label: '院校名称',
          max: 255,
          required: '请输入院校名称',
        },
      ]}
      onClose={onClose}
      onSubmit={async (values) => {
        await onSubmit({
          school_code: trim(values.school_code),
          name: trim(values.name),
        })
      }}
    />
  )
}

export function CollegeFormModal({
  open,
  title,
  initial,
  onClose,
  onSubmit,
  onParentInactive,
}: {
  open: boolean
  title: string
  initial?: { college_code: string | null; name: string }
  onClose: () => void
  onSubmit: (values: {
    college_code: string | null
    name: string
  }) => Promise<void>
  onParentInactive?: () => void
}) {
  return (
    <TextFormModal
      open={open}
      title={title}
      initial={{
        college_code: initial?.college_code ?? '',
        name: initial?.name ?? '',
      }}
      fields={[
        {
          name: 'college_code',
          label: '学院代码',
          max: 32,
          required: false,
        },
        {
          name: 'name',
          label: '学院名称',
          max: 255,
          required: '请输入学院名称',
        },
      ]}
      onClose={onClose}
      onParentInactive={onParentInactive}
      onSubmit={async (values) => {
        const code = trim(values.college_code)
        await onSubmit({
          college_code: code === '' ? null : code,
          name: trim(values.name),
        })
      }}
    />
  )
}

export function MajorFormModal({
  open,
  title,
  initial,
  onClose,
  onSubmit,
  onParentInactive,
}: {
  open: boolean
  title: string
  initial?: MajorValues
  onClose: () => void
  onSubmit: (values: MajorValues) => Promise<void>
  onParentInactive?: () => void
}) {
  const { message } = App.useApp()
  const [form] = Form.useForm<MajorValues>()
  const [saving, setSaving] = useState(false)
  const values = initial ?? {
    major_code: '',
    name: '',
    degree_type: 'academic' as const,
  }

  return (
    <Modal
      open={open}
      title={title}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      maskClosable={!saving}
      closable={!saving}
      cancelButtonProps={{ disabled: saving }}
      destroyOnHidden
      onCancel={onClose}
      onOk={() => form.submit()}
    >
      <Form
        form={form}
        layout="vertical"
        preserve={false}
        initialValues={values}
        onFinish={(submitted) => {
          if (saving) {
            return
          }
          setSaving(true)
          void onSubmit({
            major_code: trim(submitted.major_code),
            name: trim(submitted.name),
            degree_type: submitted.degree_type,
          })
            .then(onClose)
            .catch((error: unknown) => {
              const mapped = mapApiError(error)
              if (mapped.type === 'fields') {
                form.setFields(
                  mapped.fields as Parameters<typeof form.setFields>[0],
                )
                return
              }
              if (mapped.type === 'parent_inactive') {
                message.error(PARENT_INACTIVE_MESSAGE)
                onParentInactive?.()
                return
              }
              message.error(mapped.message)
            })
            .finally(() => setSaving(false))
        }}
      >
        <Form.Item
          name="major_code"
          label="专业代码"
          rules={[
            { required: true, whitespace: true, message: '请输入专业代码' },
            { max: 32, message: '不超过 32 个字符' },
          ]}
        >
          <Input maxLength={32} />
        </Form.Item>
        <Form.Item
          name="name"
          label="专业名称"
          rules={[
            { required: true, whitespace: true, message: '请输入专业名称' },
            { max: 255, message: '不超过 255 个字符' },
          ]}
        >
          <Input maxLength={255} />
        </Form.Item>
        <Form.Item
          name="degree_type"
          label="类型"
          rules={[{ required: true, message: '请选择类型' }]}
        >
          <Select
            options={[
              { value: 'academic', label: '学硕' },
              { value: 'professional', label: '专硕' },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

export function SubjectFormModal({
  open,
  title,
  initial,
  onClose,
  onSubmit,
  onParentInactive,
}: {
  open: boolean
  title: string
  initial?: SubjectValues
  onClose: () => void
  onSubmit: (values: SubjectValues) => Promise<void>
  onParentInactive?: () => void
}) {
  return (
    <TextFormModal
      open={open}
      title={title}
      initial={initial ?? { subject_code: '', name: '' }}
      fields={[
        {
          name: 'subject_code',
          label: '科目代码',
          max: 32,
          required: '请输入科目代码',
        },
        {
          name: 'name',
          label: '科目名称',
          max: 255,
          required: '请输入科目名称',
        },
      ]}
      onClose={onClose}
      onParentInactive={onParentInactive}
      onSubmit={async (values) => {
        await onSubmit({
          subject_code: trim(values.subject_code),
          name: trim(values.name),
        })
      }}
    />
  )
}

function TextFormModal({
  open,
  title,
  initial,
  fields,
  onClose,
  onSubmit,
  onParentInactive,
}: {
  open: boolean
  title: string
  initial: Record<string, string>
  fields: {
    name: string
    label: string
    max: number
    required: string | false
  }[]
  onClose: () => void
  onSubmit: (values: Record<string, string>) => Promise<void>
  onParentInactive?: () => void
}) {
  const { message } = App.useApp()
  const [form] = Form.useForm<Record<string, string>>()
  const [saving, setSaving] = useState(false)

  return (
    <Modal
      open={open}
      title={title}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      maskClosable={!saving}
      closable={!saving}
      cancelButtonProps={{ disabled: saving }}
      destroyOnHidden
      onCancel={onClose}
      onOk={() => form.submit()}
    >
      <Form
        form={form}
        layout="vertical"
        preserve={false}
        initialValues={initial}
        onFinish={(values) => {
          if (saving) {
            return
          }
          setSaving(true)
          void onSubmit(values)
            .then(onClose)
            .catch((error: unknown) => {
              const mapped = mapApiError(error)
              if (mapped.type === 'fields') {
                form.setFields(
                  mapped.fields as Parameters<typeof form.setFields>[0],
                )
                return
              }
              if (mapped.type === 'parent_inactive') {
                message.error(PARENT_INACTIVE_MESSAGE)
                onParentInactive?.()
                return
              }
              message.error(mapped.message)
            })
            .finally(() => setSaving(false))
        }}
      >
        {fields.map((field) => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.label}
            rules={[
              ...(field.required
                ? [
                    {
                      required: true,
                      whitespace: true,
                      message: field.required,
                    },
                  ]
                : []),
              { max: field.max, message: `不超过 ${field.max} 个字符` },
            ]}
          >
            <Input maxLength={field.max} />
          </Form.Item>
        ))}
      </Form>
    </Modal>
  )
}
