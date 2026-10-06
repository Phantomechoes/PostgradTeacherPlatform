import { App, Form, Input, Modal } from 'antd'
import { useEffect, useState } from 'react'
import type { TeacherProfilePatch } from '../../api/teacher'
import { mapTeacherApiError } from './teacherFormErrors'

type TeacherFormValues = {
  display_name: string
  bio?: string
}

function buildTeacherProfilePatch(
  current: { display_name: string; bio: string | null },
  values: TeacherFormValues,
): TeacherProfilePatch | null {
  const displayName = values.display_name.trim()
  const bioText = (values.bio ?? '').trim()
  const patch: TeacherProfilePatch = {}
  if (displayName !== current.display_name) {
    patch.display_name = displayName
  }
  const currentBio =
    current.bio === null || current.bio.trim() === '' ? null : current.bio
  if (bioText === '') {
    if (currentBio !== null) {
      patch.bio = null
    }
  } else if (bioText !== currentBio) {
    patch.bio = bioText
  }
  if (patch.display_name === undefined && patch.bio === undefined) {
    return null
  }
  return patch
}

export function TeacherProfileEditModal({
  open,
  displayName,
  bio,
  onClose,
  onSubmit,
}: {
  open: boolean
  displayName: string
  bio: string | null
  onClose: () => void
  onSubmit: (patch: TeacherProfilePatch) => Promise<boolean>
}) {
  const { message } = App.useApp()
  const [form] = Form.useForm<TeacherFormValues>()
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) {
      return
    }
    form.setFieldsValue({
      display_name: displayName,
      bio: bio ?? '',
    })
  }, [bio, displayName, form, open])

  return (
    <Modal
      open={open}
      title="编辑档案"
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
        initialValues={{ display_name: displayName, bio: bio ?? '' }}
        onFinish={(values) => {
          if (saving) {
            return
          }
          const patch = buildTeacherProfilePatch(
            { display_name: displayName, bio },
            values,
          )
          if (!patch) {
            message.info('没有修改')
            onClose()
            return
          }
          setSaving(true)
          void onSubmit(patch)
            .then((saved) => {
              if (saved) {
                onClose()
              }
            })
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
