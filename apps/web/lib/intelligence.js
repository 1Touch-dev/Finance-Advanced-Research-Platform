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

function buildTimelineError({ status, detail, message, raw }) {
  const error = new Error(message || 'Timeline request failed.')
  error.name = 'TimelineRequestError'
  error.status = status
  error.detail = detail
  error.raw = raw
  return error
}

function buildTimelineRequestUrl(pathname, params = {}) {
  const baseUrl = getApiBaseUrl()
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    query.set(key, String(value))
  })

  const suffix = query.toString()
  return `${baseUrl}${pathname}${suffix ? `?${suffix}` : ''}`
}

async function fetchTimelineJson(requestUrl) {
  let response

  try {
    response = await fetch(requestUrl)
  } catch (networkError) {
    const message = networkError?.message || 'Network request failed.'
    throw buildTimelineError({
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
  } catch (error) {
    raw = rawText || null
  }

  if (!response.ok) {
    const detail = raw && Object.prototype.hasOwnProperty.call(raw, 'detail')
      ? raw.detail
      : rawText || response.statusText
    const message = normalizeErrorDetail(detail) || `Timeline request failed with status ${response.status}`
    throw buildTimelineError({
      status: response.status,
      detail,
      message,
      raw,
    })
  }

  return raw
}

export async function fetchTimeline({ ticker, years = 2 }) {
  const normalizedTicker = String(ticker || '').trim().toUpperCase()

  if (!normalizedTicker) {
    throw buildTimelineError({
      status: 422,
      detail: 'ticker is required',
      message: 'Ticker is required.',
      raw: null,
    })
  }

  const requestUrl = buildTimelineRequestUrl(
    `/intelligence/timeline/${encodeURIComponent(normalizedTicker)}`,
    {
      years,
      include_price: true,
    }
  )

  return fetchTimelineJson(requestUrl)
}

export async function fetchTimelineCompare({ ticker, against, years = 2 }) {
  const normalizedTicker = String(ticker || '').trim().toUpperCase()
  const normalizedAgainst = String(against || '').trim().toUpperCase()

  if (!normalizedTicker) {
    throw buildTimelineError({
      status: 422,
      detail: 'ticker is required',
      message: 'Ticker is required.',
      raw: null,
    })
  }

  if (!normalizedAgainst) {
    throw buildTimelineError({
      status: 422,
      detail: 'against is required',
      message: 'At least one comparison ticker is required.',
      raw: null,
    })
  }

  const requestUrl = buildTimelineRequestUrl(
    `/intelligence/timeline/${encodeURIComponent(normalizedTicker)}/compare`,
    {
      against: normalizedAgainst,
      years,
    }
  )

  return fetchTimelineJson(requestUrl)
}
