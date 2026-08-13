import { getApiBaseUrl } from './api'

function normalizeErrorDetail(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item
        }
        if (item && typeof item === 'object') {
          const location = Array.isArray(item.loc) ? item.loc.join('.') : item.loc
          const message = item.msg || item.message || JSON.stringify(item)
          return location ? `${location}: ${message}` : message
        }
        return String(item)
      })
      .join('\n')
  }

  if (detail && typeof detail === 'object') {
    return detail.message || JSON.stringify(detail, null, 2)
  }

  return detail || ''
}

function looksUnsafeInternalError(text) {
  const value = String(text || '')
  if (!value) {
    return false
  }
  return [
    'traceback',
    'stack trace',
    'exception:',
    'sqlalchemy',
    'select ',
    'insert into',
    'update ',
    'delete from',
    'file "',
    ' at line ',
    'module named',
    'errno',
    'permission denied',
    'c:\\\\',
    '/app/',
    '/usr/',
    'token',
    'secret',
    'api key',
    'provider error',
  ].some((pattern) => value.toLowerCase().includes(pattern))
}

function sanitizeErrorDetail(status, detail, message) {
  const normalized = normalizeErrorDetail(detail || message || '')
  if (!normalized) {
    return status >= 500 || status === 0
      ? 'The request could not be completed right now. Please try again.'
      : ''
  }
  if ((status >= 500 || status === 0) && looksUnsafeInternalError(normalized)) {
    return 'The request could not be completed right now. Please try again.'
  }
  return normalized
}

function buildIntelligenceError({ status, detail, message, raw }) {
  const error = new Error(message || 'Request failed.')
  error.name = 'IntelligenceActivationError'
  error.status = status
  error.detail = detail
  error.raw = raw
  return error
}

async function readResponseBody(response, expectHtml = false) {
  let text = ''
  try {
    text = await response.text()
  } catch (error) {
    text = ''
  }

  if (expectHtml) {
    return {
      text,
      raw: text,
      parsed: text,
    }
  }

  let parsed = null
  try {
    parsed = text ? JSON.parse(text) : null
  } catch (error) {
    parsed = null
  }

  return {
    text,
    raw: parsed !== null ? parsed : (text || null),
    parsed: parsed !== null ? parsed : text,
  }
}

async function requestIntelligence(path, options = {}) {
  const {
    method = 'POST',
    body,
    expectHtml = false,
  } = options

  const baseUrl = getApiBaseUrl()
  const requestUrl = `${baseUrl}${path}`

  let response
  try {
    response = await fetch(requestUrl, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (networkError) {
    const message = networkError?.message || 'Network request failed.'
    throw buildIntelligenceError({
      status: 0,
      detail: message,
      message,
      raw: null,
    })
  }

  const payload = await readResponseBody(response, expectHtml)

  if (!response.ok) {
    const detail = payload.raw && typeof payload.raw === 'object' && Object.prototype.hasOwnProperty.call(payload.raw, 'detail')
      ? payload.raw.detail
      : payload.text || response.statusText
    const message = normalizeErrorDetail(detail) || `Request failed with status ${response.status}`
    throw buildIntelligenceError({
      status: response.status,
      detail,
      message,
      raw: payload.raw,
    })
  }

  return expectHtml
    ? {
        html: payload.text || '',
        raw: payload.raw,
      }
    : payload.raw
}

export function splitCommaSeparated(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function formatIntelligenceError(error) {
  const status = error?.status || 0
  const detail = sanitizeErrorDetail(status, error?.detail, error?.message)
  return {
    status,
    message: error?.message || 'Request failed.',
    detail,
    raw: error?.raw || null,
  }
}

export function fetchSelfDealingAnalysis(payload) {
  return requestIntelligence('/intelligence/self-dealing', { body: payload })
}

export function fetchNetworkAnalysis(payload) {
  return requestIntelligence('/intelligence/network', { body: payload })
}

export function fetchCorrelationAnalysis(payload) {
  return requestIntelligence('/intelligence/correlation', { body: payload })
}

export function fetchContractProbabilityAnalysis(payload) {
  return requestIntelligence('/intelligence/contract-probability', { body: payload })
}

export function createInteractiveReport(payload) {
  return requestIntelligence('/intelligence/interactive-report', {
    body: payload,
    expectHtml: true,
  })
}

export function fetchInteractiveReport(reportId) {
  return requestIntelligence(`/intelligence/${reportId}/interactive`, {
    method: 'GET',
    expectHtml: true,
  })
}
