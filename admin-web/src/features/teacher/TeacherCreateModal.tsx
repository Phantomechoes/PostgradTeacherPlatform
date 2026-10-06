import { App, Form, Input, Modal } from 'antd'
import { useState } from 'react'
import type { TeacherCreateBody } from '../../api/teacher'
import { mapTeacherApiError } from './teacherFormErrors'

type TeacherFormValues = {
  display_name: string
  bio?: string
}

export function TeacherCreateModal({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (values: TeacherCreateBody) => Promise<void>
}) {
  const { message } = App.useApp()
  const [form] = Form.useForm<TeacherFormValues>()
  const [saving, setSaving] = useState(false)

  return (
    <Modal
      open={open}
      title="新增师资"
      okText="创建"
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
        onFinish={(values) => {
          if (saving) {
            return
          }
          const displayName = values.display_name.trim()
          const bio = values.bio?.trim() ?? ''
          const body: TeacherCreateBody = { display_name: displayName }
          if (bio !== '') {
            body.bio = bio
          }
          setSaving(true)
          void onSubmit(body)
            .then(onClose)
            .catch((error: unknown) => {
              const mapped = mapTeacherApiError(error)
              if (mapped.type === 'fields') {
                const known = mapped.fields.filter(
                  (
                    field,
                  ): field is {
                    name: 'display_name' | 'bio'
                    errors: string[]
                  } => field.name === 'display_name' || field.name === 'bio',
                )
                if (known.length > 0) {
                  form.setFields(known)
                }
                if (known.length !== mapped.fields.length) {
                  const other = mapped.fields.find(
                    (field) =>
                      field.name !== 'display_name' && field.name !== 'bio',
                  )
                  message.error(other?.errors[0] ?? '请求参数不正确')
                }
                return
              }
              message.error(mapped.message)
            })
            .finally(() => setSaving(false))
        }}
      >
        <Form.Item
          name="display_name"
          label="名称"
          rules={[
            { required: true, whitespace: true, message: '请输入名称' },
            { max: 255, message: '名称不能超过 255 个字符' },
          ]}
        >
          <Input maxLength={255} />
        </Form.Item>
        <Form.Item
          name="bio"
          label="简介"
          rules={[
            {
              validator: async (_, value: unknown) => {
                if (typeof value !== 'string' || value === '') {
                  return
                }
                if (value.trim() === '') {
                  throw new Error('简介不能只包含空白')
                }
              },
            },
          ]}
        >
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
