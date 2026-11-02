export interface ApiError {
  status: number | null    // null when the request never reached the server
  message: string
  fields: Record<string, string>    // message per form field, e.g. { load_lb: '...' }
}

export const NETWORK_MESSAGE = "Can't reach the server. Check your connection and try again."

// Used when the body has no usable {error} text, e.g. an HTML page from the host.
const FALLBACK: Record<number, string> = {
  429: 'Too many searches. Please wait a minute and try again.',
  503: 'The weather service is busy. Please try again in a minute.',
  504: 'A map or weather service took too long. Please try again.',
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

// 400 is DRF's {field: [messages]}; every other backend error is {error} (see backend/routing/views.py).
export function toApiError(status: number, body: unknown): ApiError {
  if (status === 400 && isRecord(body)) {
    const fields: Record<string, string> = {}
    for (const [field, messages] of Object.entries(body)) {
      if (Array.isArray(messages) && typeof messages[0] === 'string') fields[field] = messages[0]
    }
    return { status, message: 'Please fix the highlighted fields.', fields }
  }
  const text = isRecord(body) && typeof body.error === 'string' ? body.error : null
  const field = isRecord(body) && typeof body.field === 'string' ? body.field : null
  const message = text ?? FALLBACK[status] ?? `Something went wrong on the server (HTTP ${status}). Please try again.`
  return { status, message, fields: text && field ? { [field]: text } : {} }
}

// An error that happened in the browser, before or instead of a server answer.
export function clientError(message: string): ApiError {
  return { status: null, message, fields: {} }
}

export function isApiError(value: unknown): value is ApiError {
  return isRecord(value) && typeof value.message === 'string' && isRecord(value.fields)
}
