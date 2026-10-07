import { ApiError } from '../../api/client'

const TEACHER_MESSAGES: Record<string, string> = {
  not_found: '请求的师资或录取记录不存在',
  duplicate_admission: '已存在相同录取信息',
  duplicate_teach_subject: '可教授科目关系重复',
  parent_inactive: '当前师资已停用，不能新增录取或新增可教授科目',
  invalid_reference: '引用的数据不存在',
  inactive_reference: '新选择的引用已停用',
  reference_scope_mismatch: '学院或专业不属于当前院校',
  catalog_identity_mismatch:
    '所选招生目录与当前录取院校、学院、专业、年份或学习方式不一致',
  check_violation: '提交的数据不符合校验规则',
  empty_patch: '没有可保存的修改',
}

export type TeacherFieldError = {
  name: string
  errors: string[]
}

export type TeacherFormError =
  | { type: 'fields'; fields: TeacherFieldError[] }
  | { type: 'message'; message: string }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function fieldName(loc: unknown): string | undefined {
  if (!Array.isArray(loc)) {
    return undefined
  }
  const names = loc.filter((part): part is string => typeof part === 'string')
  return names.filter((name) => name !== 'body').at(-1)
}

function validationFields(errors: unknown[] | undefined): TeacherFieldError[] {
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

export function mapTeacherApiError(error: unknown): TeacherFormError {
  if (!(error instanceof ApiError)) {
    return { type: 'message', message: '请求失败' }
  }
  const codeMessage = error.code ? TEACHER_MESSAGES[error.code] : undefined
  if (codeMessage) {
    return { type: 'message', message: codeMessage }
  }
  const fields = validationFields(error.validationErrors)
  if (fields.length > 0) {
    return { type: 'fields', fields }
  }
  return { type: 'message', message: error.message }
}

export function teacherErrorText(error: unknown): string {
  const mapped = mapTeacherApiError(error)
  if (mapped.type === 'message') {
    return mapped.message
  }
  return mapped.fields[0]?.errors[0] ?? '请求失败'
}
