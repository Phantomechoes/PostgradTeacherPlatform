export class ApiError extends Error {
  readonly status?: number
  readonly code?: string
  readonly validationErrors?: unknown[]

  constructor(
    message: string,
    options?: {
      status?: number
      code?: string
      validationErrors?: unknown[]
    },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = options?.status
    this.code = options?.code
    this.validationErrors = options?.validationErrors
  }
}

type JsonMethod = 'GET' | 'POST' | 'PUT' | 'PATCH'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function domainDetail(
  value: unknown,
): { code: string; message: string } | undefined {
  if (!isRecord(value) || !isRecord(value.detail)) {
    return undefined
  }
  const { code, message } = value.detail
  if (typeof code === 'string' && typeof message === 'string') {
    return { code, message }
  }
  return undefined
}

function validationDetail(value: unknown): unknown[] | undefined {
  if (!isRecord(value) || !Array.isArray(value.detail)) {
    return undefined
  }
  return value.detail
}

function fallbackMessage(status: number): string {
  if (status >= 500) {
    return '服务器错误'
  }
  if (status === 404) {
    return '未找到'
  }
  return '请求失败'
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    return new ApiError(fallbackMessage(response.status), {
      status: response.status,
    })
  }
  const domain = domainDetail(payload)
  if (domain) {
    return new ApiError(domain.message, {
      status: response.status,
      code: domain.code,
    })
  }
  const validationErrors = validationDetail(payload)
  if (validationErrors) {
    return new ApiError('请求参数不正确', {
      status: response.status,
      validationErrors,
    })
  }
  return new ApiError(fallbackMessage(response.status), {
    status: response.status,
  })
}

export type RequestOptions = {
  signal?: AbortSignal
}

export function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === 'AbortError') ||
    (isRecord(error) && error.name === 'AbortError')
  )
}

async function requestJson<T>(
  method: JsonMethod,
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      method,
      signal: options?.signal,
      headers:
        body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if (isAbortError(error)) {
      throw error
    }
    throw new ApiError('无法连接服务器')
  }
  if (!response.ok) {
    throw await toApiError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export function getJson<T>(path: string, options?: RequestOptions): Promise<T> {
  return requestJson<T>('GET', path, undefined, options)
}

export function postJson<T>(
  path: string,
  body: unknown,
  options?: RequestOptions,
): Promise<T> {
  return requestJson<T>('POST', path, body, options)
}

export function putJson<T>(
  path: string,
  body: unknown,
  options?: RequestOptions,
): Promise<T> {
  return requestJson<T>('PUT', path, body, options)
}

export function patchJson<T>(
  path: string,
  body: unknown,
  options?: RequestOptions,
): Promise<T> {
  return requestJson<T>('PATCH', path, body, options)
}
