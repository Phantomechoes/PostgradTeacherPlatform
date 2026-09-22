import { ApiError } from './client'

const CATALOG_MESSAGES: Record<string, string> = {
  duplicate_catalog_offering:
    '该院校下已存在相同学院、专业、年份和学习方式的招生目录',
  invalid_reference: '引用的学校、学院、专业或科目不存在',
  inactive_reference: '引用的学校、学院、专业或科目已停用，无法完成此操作',
  reference_scope_mismatch: '学院、专业或科目不属于当前院校',
}

const DUPLICATE_FIELDS: Record<string, { field: string; message: string }> = {
  duplicate_school_code: { field: 'school_code', message: '院校代码已存在' },
  duplicate_college_code: { field: 'college_code', message: '学院代码已存在' },
  duplicate_major_code: { field: 'major_code', message: '专业代码已存在' },
  duplicate_national_subject_code: {
    field: 'subject_code',
    message: '科目代码已存在',
  },
  duplicate_school_subject_code: {
    field: 'subject_code',
    message: '科目代码已存在',
  },
}

export type FieldError = {
  name: string
  errors: string[]
}

export type MappedFormError =
  | { type: 'fields'; fields: FieldError[] }
  | { type: 'parent_inactive' }
  | { type: 'message'; message: string }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function fieldName(loc: unknown): string | undefined {
  if (!Array.isArray(loc)) {
    return undefined
  }
  const names = loc.filter((part): part is string => typeof part === 'string')
  const field = names.filter((name) => name !== 'body').at(-1)
  return field
}

function validationFields(errors: unknown[] | undefined): FieldError[] {
  const grouped = new Map<string, string[]>()
  for (const item of errors ?? []) {
    if (!isRecord(item) || typeof item.msg !== 'string') {
      continue
    }
    const name = fieldName(item.loc)
    if (!name) {
      continue
    }
    const current = grouped.get(name) ?? []
    current.push(item.msg)
    grouped.set(name, current)
  }
  return [...grouped.entries()].map(([name, messages]) => ({
    name,
    errors: messages,
  }))
}

export function mapApiError(error: unknown): MappedFormError {
  if (!(error instanceof ApiError)) {
    return { type: 'message', message: '请求失败' }
  }
  const duplicate = error.code ? DUPLICATE_FIELDS[error.code] : undefined
  if (duplicate) {
    return {
      type: 'fields',
      fields: [{ name: duplicate.field, errors: [duplicate.message] }],
    }
  }
  if (error.code === 'parent_inactive') {
    return { type: 'parent_inactive' }
  }
  const catalogMessage = error.code ? CATALOG_MESSAGES[error.code] : undefined
  if (catalogMessage) {
    return { type: 'message', message: catalogMessage }
  }
  const fields = validationFields(error.validationErrors)
  if (fields.length > 0) {
    return { type: 'fields', fields }
  }
  return { type: 'message', message: error.message }
}

export function errorText(error: unknown): string {
  const mapped = mapApiError(error)
  if (mapped.type === 'message') {
    return mapped.message
  }
  if (mapped.type === 'parent_inactive') {
    return '院校已停用，无法新增下级数据。'
  }
  return mapped.fields[0]?.errors[0] ?? '请求失败'
}
