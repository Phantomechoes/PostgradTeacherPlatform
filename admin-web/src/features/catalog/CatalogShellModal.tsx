import { App, Form, InputNumber, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { errorText, mapApiError } from '../../api/formErrors'
import { listColleges, listMajors } from '../../api/masterData'
import type {
  CatalogShellCreate,
  CollegeAdmin,
  MajorAdmin,
  SchoolAdmin,
  StudyMode,
} from '../../api/types'
import { entityLabel, STUDY_MODE_LABEL } from './labels'

type ShellForm = {
  school_id: number
  college_id: number
  major_id: number
  admission_year: number
  study_mode: StudyMode
}

export function CatalogShellModal({
  open,
  schools,
  defaultSchoolId,
  onClose,
  onSubmit,
}: {
  open: boolean
  schools: SchoolAdmin[]
  defaultSchoolId?: number
  onClose: () => void
  onSubmit: (values: CatalogShellCreate) => Promise<void>
}) {
  const { message } = App.useApp()
  const [form] = Form.useForm<ShellForm>()
  const [saving, setSaving] = useState(false)
  const schoolId = Form.useWatch('school_id', form)
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

  useEffect(() => {
    if (!open) {
      return
    }
    form.setFieldsValue({
      school_id: defaultSchoolId,
      college_id: undefined,
      major_id: undefined,
      admission_year: new Date().getFullYear(),
      study_mode: 'full_time',
    })
  }, [defaultSchoolId, form, open])

  useEffect(() => {
    if (!open || !schoolId) {
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
      .catch(() => {
        if (!controller.signal.aborted) {
          setChildLists((current) =>
            current.key === key ? { key, colleges: [], majors: [] } : current,
          )
        }
      })
    return () => controller.abort()
  }, [open, schoolId])

  return (
    <Modal
      open={open}
      title="新增招生目录"
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
          setSaving(true)
          void onSubmit({
            school_id: values.school_id,
            college_id: values.college_id,
            major_id: values.major_id,
            admission_year: values.admission_year,
            study_mode: values.study_mode,
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
              message.error(errorText(error))
            })
            .finally(() => setSaving(false))
        }}
      >
        <Form.Item
          name="school_id"
          label="院校"
          rules={[{ required: true, message: '请选择院校' }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            onChange={() => {
              form.setFieldsValue({
                college_id: undefined,
                major_id: undefined,
              })
            }}
            options={schools.map((school) => ({
              value: school.id,
              label: entityLabel(
                school.school_code,
                school.name,
                school.is_active,
              ),
              disabled: !school.is_active,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="college_id"
          label="学院"
          rules={[{ required: true, message: '请选择学院' }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            disabled={!schoolId}
            options={colleges.map((college) => ({
              value: college.id,
              label: entityLabel(
                college.college_code,
                college.name,
                college.is_active,
              ),
              disabled: !college.is_active,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="major_id"
          label="专业"
          rules={[{ required: true, message: '请选择专业' }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            disabled={!schoolId}
            options={majors.map((major) => ({
              value: major.id,
              label: entityLabel(major.major_code, major.name, major.is_active),
              disabled: !major.is_active,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="admission_year"
          label="招生年份"
          rules={[{ required: true, message: '请输入招生年份' }]}
        >
          <InputNumber min={2000} max={9999} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="study_mode"
          label="学习方式"
          rules={[{ required: true, message: '请选择学习方式' }]}
        >
          <Select
            options={(Object.keys(STUDY_MODE_LABEL) as StudyMode[]).map(
              (value) => ({
                value,
                label: STUDY_MODE_LABEL[value],
              }),
            )}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
