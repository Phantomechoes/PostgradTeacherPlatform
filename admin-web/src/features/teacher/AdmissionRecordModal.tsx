import { App, Form, InputNumber, Modal, Select } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { isAbortError } from '../../api/client'
import { getCatalog, listCatalogs } from '../../api/catalog'
import { listAllSchools, listColleges, listMajors } from '../../api/masterData'
import type {
  AdmissionRecordCreateBody,
  AdmissionRecordPatch,
} from '../../api/teacher'
import type {
  AdmissionRecordAdmin,
  CatalogAdminSummary,
  CollegeAdmin,
  MajorAdmin,
  SchoolAdmin,
  StudyMode,
} from '../../api/types'
import { STUDY_MODE_LABEL } from '../catalog/labels'
import {
  buildAdmissionCreate,
  buildAdmissionPatch,
  catalogSelectOptions,
  collegeOptionLabel,
  emptyAdmissionFormValues,
  identityLinkFrom,
  majorOptionLabel,
  schoolOptionLabel,
  toAdmissionFormValues,
  withCurrentReference,
  type AdmissionFormValues,
} from './admissionRecordHelpers'
import { mapTeacherApiError, teacherErrorText } from './teacherFormErrors'

const ADMISSION_FIELDS = [
  'school_id',
  'college_id',
  'major_id',
  'admission_year',
  'study_mode',
  'admission_catalog_id',
  'initial_total',
  'retest_total',
  'final_total',
] as const

type AdmissionFieldName = (typeof ADMISSION_FIELDS)[number]

function isAdmissionField(name: string): name is AdmissionFieldName {
  return ADMISSION_FIELDS.some((field) => field === name)
}

const STUDY_MODE_OPTIONS = (Object.keys(STUDY_MODE_LABEL) as StudyMode[]).map(
  (value) => ({ value, label: STUDY_MODE_LABEL[value] }),
)

export function AdmissionRecordModal({
  open,
  record,
  onClose,
  onCreate,
  onUpdate,
}: {
  open: boolean
  record: AdmissionRecordAdmin | null
  onClose: () => void
  onCreate: (body: AdmissionRecordCreateBody) => Promise<boolean>
  onUpdate: (id: number, patch: AdmissionRecordPatch) => Promise<boolean>
}) {
  const { message } = App.useApp()
  const [form] = Form.useForm<AdmissionFormValues>()
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const ignoreLinkage = useRef(false)
  const linkage = useRef(identityLinkFrom(emptyAdmissionFormValues()))
  const [schools, setSchools] = useState<SchoolAdmin[] | null>(null)
  const [colleges, setColleges] = useState<CollegeAdmin[]>([])
  const [majors, setMajors] = useState<MajorAdmin[]>([])
  const [refSchoolId, setRefSchoolId] = useState<number | null>(null)
  const [catalogs, setCatalogs] = useState<CatalogAdminSummary[]>([])
  const [catalogKey, setCatalogKey] = useState<string | null>(null)
  const [currentCatalog, setCurrentCatalog] =
    useState<CatalogAdminSummary | null>(null)
  const [resolvedCatalogId, setResolvedCatalogId] = useState<number | null>(
    null,
  )

  const schoolId = Form.useWatch('school_id', form)
  const collegeId = Form.useWatch('college_id', form)
  const majorId = Form.useWatch('major_id', form)
  const admissionYear = Form.useWatch('admission_year', form)
  const studyMode = Form.useWatch('study_mode', form)
  const catalogId = Form.useWatch('admission_catalog_id', form)

  useEffect(() => {
    if (!open) {
      return
    }
    const values = record
      ? toAdmissionFormValues(record)
      : emptyAdmissionFormValues()
    ignoreLinkage.current = true
    linkage.current = identityLinkFrom(values)
    form.setFieldsValue(values)
    const timer = window.setTimeout(() => {
      ignoreLinkage.current = false
    }, 0)
    return () => window.clearTimeout(timer)
  }, [form, open, record])

  useEffect(() => {
    if (!open) {
      return
    }
    const controller = new AbortController()
    listAllSchools('active', { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) {
          setSchools(items)
        }
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) {
          return
        }
        setSchools([])
        message.error(teacherErrorText(error))
      })
    return () => controller.abort()
  }, [message, open])

  useEffect(() => {
    if (!open || typeof schoolId !== 'number') {
      return
    }
    const requestedSchoolId = schoolId
    const controller = new AbortController()
    Promise.all([
      listColleges(requestedSchoolId, 'active', { signal: controller.signal }),
      listMajors(requestedSchoolId, 'active', { signal: controller.signal }),
    ])
      .then(([collegeItems, majorItems]) => {
        if (controller.signal.aborted) {
          return
        }
        setColleges(collegeItems)
        setMajors(majorItems)
        setRefSchoolId(requestedSchoolId)
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) {
          return
        }
        setColleges([])
        setMajors([])
        setRefSchoolId(requestedSchoolId)
        message.error(teacherErrorText(error))
      })
    return () => controller.abort()
  }, [message, open, schoolId])

  const tupleKey =
    open &&
    typeof schoolId === 'number' &&
    typeof collegeId === 'number' &&
    typeof majorId === 'number' &&
    typeof admissionYear === 'number' &&
    studyMode !== undefined
      ? `${schoolId}|${collegeId}|${majorId}|${admissionYear}|${studyMode}`
      : ''

  useEffect(() => {
    if (tupleKey === '' || studyMode === undefined) {
      return
    }
    if (
      typeof schoolId !== 'number' ||
      typeof collegeId !== 'number' ||
      typeof majorId !== 'number' ||
      typeof admissionYear !== 'number'
    ) {
      return
    }
    const requestedKey = tupleKey
    const controller = new AbortController()
    listCatalogs(
      {
        schoolId,
        collegeId,
        majorId,
        admissionYear,
        studyMode,
        status: 'all',
        page: 1,
        pageSize: 100,
      },
      { signal: controller.signal },
    )
      .then((page) => {
        if (!controller.signal.aborted) {
          setCatalogs(page.items)
          setCatalogKey(requestedKey)
        }
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) {
          return
        }
        setCatalogs([])
        setCatalogKey(requestedKey)
      })
    return () => controller.abort()
  }, [admissionYear, collegeId, majorId, schoolId, studyMode, tupleKey])

  const wantedCatalogId =
    open && record?.admission_catalog_id != null
      ? record.admission_catalog_id
      : null

  useEffect(() => {
    if (wantedCatalogId === null) {
      return
    }
    const controller = new AbortController()
    getCatalog(wantedCatalogId, { signal: controller.signal })
      .then((detail) => {
        if (!controller.signal.aborted) {
          setCurrentCatalog(detail)
          setResolvedCatalogId(wantedCatalogId)
        }
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) {
          return
        }
        setCurrentCatalog(null)
        setResolvedCatalogId(wantedCatalogId)
      })
    return () => controller.abort()
  }, [wantedCatalogId])

  function clearCatalog() {
    form.setFieldValue('admission_catalog_id', null)
  }

  function onSchoolChange(value: number) {
    if (ignoreLinkage.current || linkage.current.school_id === value) {
      return
    }
    linkage.current = {
      ...linkage.current,
      school_id: value,
      college_id: undefined,
      major_id: undefined,
    }
    form.setFieldsValue({
      college_id: undefined,
      major_id: undefined,
      admission_catalog_id: null,
    })
  }

  function onCollegeChange(value: number) {
    if (ignoreLinkage.current || linkage.current.college_id === value) {
      return
    }
    linkage.current = { ...linkage.current, college_id: value }
    clearCatalog()
  }

  function onMajorChange(value: number) {
    if (ignoreLinkage.current || linkage.current.major_id === value) {
      return
    }
    linkage.current = { ...linkage.current, major_id: value }
    clearCatalog()
  }

  function onYearChange(value: number | null) {
    const next = typeof value === 'number' ? value : undefined
    if (ignoreLinkage.current || linkage.current.admission_year === next) {
      return
    }
    linkage.current = { ...linkage.current, admission_year: next }
    clearCatalog()
  }

  function onModeChange(value: StudyMode) {
    if (ignoreLinkage.current || linkage.current.study_mode === value) {
      return
    }
    linkage.current = { ...linkage.current, study_mode: value }
    clearCatalog()
  }

  const tupleReady = tupleKey !== ''
  const schoolsLoading = open && schools === null
  const refsLoading =
    open && typeof schoolId === 'number' && refSchoolId !== schoolId
  const visibleColleges = refSchoolId === schoolId ? colleges : []
  const visibleMajors = refSchoolId === schoolId ? majors : []
  const catalogsLoading = tupleKey !== '' && catalogKey !== tupleKey
  const visibleCatalogs =
    tupleKey !== '' && catalogKey === tupleKey ? catalogs : []
  const resolvedCatalog =
    wantedCatalogId !== null && resolvedCatalogId === wantedCatalogId
      ? currentCatalog
      : null
  const schoolOptions = withCurrentReference(
    schools ?? [],
    record?.school ?? null,
    schoolId,
    schoolOptionLabel,
  )
  const collegeOptions = withCurrentReference(
    visibleColleges,
    record && schoolId === record.school.id ? record.college : null,
    collegeId,
    collegeOptionLabel,
  )
  const majorOptions = withCurrentReference(
    visibleMajors,
    record && schoolId === record.school.id ? record.major : null,
    majorId,
    majorOptionLabel,
  )
  const catalogOptions = catalogSelectOptions(
    visibleCatalogs,
    catalogId,
    resolvedCatalog,
  )

  function applyFieldError(error: unknown) {
    const mapped = mapTeacherApiError(error)
    if (mapped.type === 'fields') {
      const known = mapped.fields.filter(
        (field): field is { name: AdmissionFieldName; errors: string[] } =>
          isAdmissionField(field.name),
      )
      if (known.length > 0) {
        form.setFields(known)
      }
      if (known.length !== mapped.fields.length) {
        const other = mapped.fields.find(
          (field) => !isAdmissionField(field.name),
        )
        message.error(other?.errors[0] ?? '请求参数不正确')
      }
      return
    }
    message.error(mapped.message)
  }

  return (
    <Modal
      open={open}
      title={record ? '编辑录取记录' : '新增录取记录'}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      maskClosable={!saving}
      closable={!saving}
      cancelButtonProps={{ disabled: saving }}
      destroyOnHidden
      width={640}
      onCancel={onClose}
      onOk={() => form.submit()}
    >
      <Form
        form={form}
        layout="vertical"
        preserve={false}
        initialValues={
          record ? toAdmissionFormValues(record) : emptyAdmissionFormValues()
        }
        onFinish={(values) => {
          if (savingRef.current) {
            return
          }
          const submit = (action: () => Promise<boolean>) => {
            savingRef.current = true
            setSaving(true)
            void action()
              .then((saved) => {
                if (saved) {
                  onClose()
                }
              })
              .catch((error: unknown) => {
                applyFieldError(error)
              })
              .finally(() => {
                savingRef.current = false
                setSaving(false)
              })
          }
          if (!record) {
            const body = buildAdmissionCreate(values)
            if (!body) {
              message.error('请完整填写录取信息')
              return
            }
            submit(() => onCreate(body))
            return
          }
          const patch = buildAdmissionPatch(record, values)
          if (!patch) {
            message.info('没有修改')
            onClose()
            return
          }
          submit(() => onUpdate(record.id, patch))
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
            placeholder="请选择院校"
            loading={schoolsLoading}
            options={schoolOptions}
            onChange={onSchoolChange}
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
            placeholder="请选择学院"
            disabled={typeof schoolId !== 'number'}
            loading={refsLoading}
            options={collegeOptions}
            onChange={onCollegeChange}
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
            placeholder="请选择专业"
            disabled={typeof schoolId !== 'number'}
            loading={refsLoading}
            options={majorOptions}
            onChange={onMajorChange}
          />
        </Form.Item>
        <Form.Item
          name="admission_year"
          label="录取年份"
          rules={[
            { required: true, message: '请输入录取年份' },
            {
              validator: async (_, value: unknown) => {
                if (value === undefined || value === null || value === '') {
                  return
                }
                if (
                  typeof value !== 'number' ||
                  !Number.isInteger(value) ||
                  value < 2000
                ) {
                  throw new Error('录取年份不能早于 2000')
                }
              },
            },
          ]}
        >
          <InputNumber
            min={2000}
            precision={0}
            style={{ width: '100%' }}
            onChange={onYearChange}
          />
        </Form.Item>
        <Form.Item
          name="study_mode"
          label="学习方式"
          rules={[{ required: true, message: '请选择学习方式' }]}
        >
          <Select
            placeholder="请选择学习方式"
            options={STUDY_MODE_OPTIONS}
            onChange={onModeChange}
          />
        </Form.Item>
        <Form.Item name="admission_catalog_id" label="招生目录">
          <Select
            allowClear
            placeholder={
              tupleReady
                ? '不关联招生目录'
                : '请先完成院校、学院、专业、年份和学习方式'
            }
            disabled={!tupleReady}
            loading={catalogsLoading}
            options={catalogOptions}
          />
        </Form.Item>
        <Form.Item name="initial_total" label="初试总分">
          <InputNumber min={0} precision={2} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="retest_total" label="复试总分">
          <InputNumber min={0} precision={2} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="final_total" label="最终总分">
          <InputNumber min={0} precision={2} style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
