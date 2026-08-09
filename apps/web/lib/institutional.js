import { getApiBaseUrl } from './api'

function appendQueryParam(params, key, value) {
  if (value === null || value === undefined) {
    return
  }

  if (typeof value === 'string' && value.trim() === '') {
    return
  }

  params.set(key, String(value))
}

function normalizeErrorDetail(detail) {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item
        }

        if (item && typeof item === 'object') {
          const location = Array.isArray(item.loc) ? item.loc.join('.') : item.loc
          const message = item.msg || JSON.stringify(item)
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

function buildInstitutionalError({ status, detail, message, raw }) {
  const error = new Error(message || 'Request failed.')
  error.name = 'InstitutionalPositionDiffError'
  error.status = status
  error.detail = detail
  error.raw = raw
  return error
}

export async function fetchInstitutionalPositionDiff(query = {}) {
  const baseUrl = getApiBaseUrl()
  const params = new URLSearchParams()

  appendQueryParam(params, 'institution_cik', query.institution_cik)
  appendQueryParam(params, 'current_period', query.current_period)
  appendQueryParam(params, 'previous_period', query.previous_period)
  appendQueryParam(params, 'status', query.status)
  appendQueryParam(params, 'ticker', query.ticker)
  appendQueryParam(params, 'cusip', query.cusip)
  appendQueryParam(params, 'sort_by', query.sort_by)
  appendQueryParam(params, 'sort_dir', query.sort_dir)
  appendQueryParam(params, 'limit', query.limit)
  appendQueryParam(params, 'offset', query.offset)

  const requestUrl = `${baseUrl}/market/institutional/position-diff?${params.toString()}`
  let response

  try {
    response = await fetch(requestUrl)
  } catch (networkError) {
    const message = networkError?.message || 'Network request failed.'
    throw buildInstitutionalError({
      status: 0,
      detail: message,
      message,
      raw: null,
    })
  }

  let rawText = ''
  try {
    rawText = await response.text()
  } catch (readError) {
    rawText = ''
  }

  let raw = null
  try {
    raw = rawText ? JSON.parse(rawText) : null
  } catch (parseError) {
    raw = rawText || null
  }

  if (!response.ok) {
    const detail = raw && Object.prototype.hasOwnProperty.call(raw, 'detail')
      ? raw.detail
      : rawText || response.statusText
    const message = normalizeErrorDetail(detail) || `Request failed with status ${response.status}`

    throw buildInstitutionalError({
      status: response.status,
      detail,
      message,
      raw,
    })
  }

  return raw
}
