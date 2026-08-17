import Head from 'next/head'
import { useRouter } from 'next/router'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

import { fetchTimeline, fetchTimelineCompare } from '../lib/intelligence'
import styles from '../src/styles/Page.module.css'
import tStyles from '../src/styles/Timeline.module.css'

const YEAR_OPTIONS = [1, 2, 5]
const TICKER_PATTERN = /^[A-Z][A-Z0-9.\-]{0,9}$/
const MAX_COMPARE_TICKERS = 5
const TICKER_COLORS = ['#818cf8', '#38bdf8', '#4ade80', '#fbbf24', '#f472b6', '#fb7185']
const CATEGORY_CONFIG = [
  { id: 'all', label: 'All', color: '#c7d2fe' },
  { id: 'financial', label: 'Financial', color: '#4ade80' },
  { id: 'insider', label: 'Insider', color: '#fbbf24' },
  { id: 'governance', label: 'Governance', color: '#f472b6' },
  { id: 'market', label: 'Market', color: '#60a5fa' },
  { id: 'strategic', label: 'Strategic', color: '#818cf8' },
  { id: 'other', label: 'Other', color: '#94a3b8' },
]
const CATEGORY_MAP = Object.fromEntries(CATEGORY_CONFIG.map((item) => [item.id, item]))
const DEFAULT_CATEGORY = CATEGORY_MAP.other

function normalizeTicker(value) {
  return String(value || '').trim().toUpperCase()
}

function normalizeYears(value) {
  const numeric = Number.parseInt(String(value || ''), 10)
  return YEAR_OPTIONS.includes(numeric) ? numeric : 2
}

function normalizeCompareInput(value) {
  return String(value || '')
    .split(',')
    .map((item) => normalizeTicker(item))
    .filter(Boolean)
    .join(',')
}

function parseCompareTickers(value, primaryTicker = '') {
  const primary = normalizeTicker(primaryTicker)
  const seen = new Set(primary ? [primary] : [])
  const valid = []
  const invalid = []
  let limitApplied = false

  String(value || '')
    .split(',')
    .map((item) => normalizeTicker(item))
    .filter(Boolean)
    .forEach((ticker) => {
      if (seen.has(ticker)) {
        return
      }

      if (!TICKER_PATTERN.test(ticker)) {
        invalid.push(ticker)
        return
      }

      if (valid.length >= MAX_COMPARE_TICKERS) {
        limitApplied = true
        return
      }

      seen.add(ticker)
      valid.push(ticker)
    })

  return {
    valid,
    invalid,
    limitApplied,
    normalized: valid.join(','),
  }
}

function buildDisplayCompare(value, primaryTicker = '') {
  return parseCompareTickers(value, primaryTicker).normalized
}

function formatDate(value) {
  if (!value) {
    return 'Unknown date'
  }

  const parsed = new Date(`${value}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function formatPrice(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return `$${Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatPercent(value) {
  if (value === null || value === undefined || value === '') {
    return ''
  }

  const numeric = Number(value)
  const prefix = numeric > 0 ? '+' : ''
  return `${prefix}${numeric.toFixed(2)}%`
}

function formatWarning(warning) {
  if (!warning) {
    return ''
  }

  if (warning.detail) {
    return warning.detail
  }

  if (warning.code) {
    return warning.code.replace(/_/g, ' ')
  }

  return 'A timeline source was unavailable for this request.'
}

function getEventCategory(category) {
  return CATEGORY_MAP[category] || DEFAULT_CATEGORY
}

function getTickerColor(ticker, colorMap) {
  return colorMap[ticker] || TICKER_COLORS[0]
}

function normalizeSinglePayload(payload) {
  return {
    mode: 'single',
    titleTicker: payload?.ticker || '',
    entityName: payload?.entity_name || payload?.ticker || '',
    tickers: payload?.ticker ? [payload.ticker] : [],
    primaryTicker: payload?.ticker || '',
    compareTickers: [],
    period: payload?.period || null,
    events: Array.isArray(payload?.events)
      ? payload.events.map((event) => ({
        ...event,
        ticker: event?.ticker || payload?.ticker || '',
      }))
      : [],
    priceSeriesByTicker: payload?.ticker
      ? {
          [payload.ticker]: Array.isArray(payload?.price_series) ? payload.price_series : [],
        }
      : {},
    summary: payload?.summary || { total_events: 0, by_category: {}, most_significant: [] },
    partial: Boolean(payload?.partial),
    warnings: Array.isArray(payload?.warnings) ? payload.warnings : [],
  }
}

function normalizeComparePayload(payload) {
  const tickers = Array.isArray(payload?.tickers) ? payload.tickers : []
  const seriesMap = {}

  ;(payload?.price_series || []).forEach((entry) => {
    if (!entry?.ticker) {
      return
    }
    seriesMap[entry.ticker] = Array.isArray(entry.points) ? entry.points : []
  })

  return {
    mode: 'compare',
    titleTicker: payload?.primary_ticker || tickers[0] || '',
    entityName: payload?.primary_ticker || tickers[0] || '',
    tickers,
    primaryTicker: payload?.primary_ticker || tickers[0] || '',
    compareTickers: tickers.slice(1),
    period: payload?.period || null,
    events: Array.isArray(payload?.events) ? payload.events : [],
    priceSeriesByTicker: seriesMap,
    summary: payload?.summary || { total_events: 0, by_ticker: {}, by_category: {}, most_significant: [] },
    partial: Boolean(payload?.partial),
    warnings: Array.isArray(payload?.warnings) ? payload.warnings : [],
  }
}

function buildChartModel(priceSeriesByTicker, events, tickers, colorMap) {
  const seriesMap = priceSeriesByTicker || {}
  const rowsByDate = new Map()
  const markerGroups = {}

  tickers.forEach((ticker) => {
    const points = [...(seriesMap[ticker] || [])].sort((left, right) => left.date.localeCompare(right.date))
    markerGroups[ticker] = []

    points.forEach((point) => {
      if (!rowsByDate.has(point.date)) {
        rowsByDate.set(point.date, { date: point.date })
      }
      const row = rowsByDate.get(point.date)
      row[ticker] = point.close
    })
  })

  const rows = [...rowsByDate.values()].sort((left, right) => left.date.localeCompare(right.date))
  const closeByTickerDate = new Map()

  tickers.forEach((ticker) => {
    ;(seriesMap[ticker] || []).forEach((point) => {
      closeByTickerDate.set(`${ticker}:${point.date}`, point.close)
    })
  })

  ;(events || []).forEach((event) => {
    const ticker = event.ticker
    if (!ticker || !markerGroups[ticker]) {
      return
    }

    const plottedClose = event.related_price?.close ?? closeByTickerDate.get(`${ticker}:${event.date}`)
    if (plottedClose === null || plottedClose === undefined) {
      return
    }

    markerGroups[ticker].push({
      ticker,
      date: event.date,
      close: plottedClose,
      eventId: event.id,
      title: event.title,
      category: event.category,
      significance: event.significance,
      source: event.source,
      relatedPrice: event.related_price || null,
      tickerColor: getTickerColor(ticker, colorMap),
    })
  })

  return { chartRows: rows, markerGroups }
}

function TimelineTooltip({ active, payload, label, isCompare }) {
  if (!active || !payload || !payload.length) {
    return null
  }

  const markerEntry = payload.find((entry) => entry.payload?.eventId)
  const marker = markerEntry?.payload
  const priceEntries = payload.filter((entry) => !entry.payload?.eventId && typeof entry.value === 'number')

  return (
    <div className={tStyles.tooltip}>
      <div className={tStyles.tooltipDate}>{formatDate(marker?.date || label)}</div>
      {marker ? (
        <>
          <div className={tStyles.tooltipCategory}>{getEventCategory(marker.category).label}</div>
          <div className={tStyles.tooltipTitle}>
            {marker.ticker ? `${marker.ticker} - ` : ''}
            {marker.title}
          </div>
          <div className={tStyles.tooltipMeta}>
            <span>Significance {marker.significance}</span>
            {marker.source ? <span>{marker.source}</span> : null}
          </div>
          <div className={tStyles.tooltipPrice}>
            {marker.relatedPrice?.close !== undefined ? formatPrice(marker.relatedPrice.close) : formatPrice(marker.close)}
            {marker.relatedPrice?.change_pct !== undefined ? ` ${formatPercent(marker.relatedPrice.change_pct)}` : ''}
          </div>
        </>
      ) : (
        <>
          <div className={tStyles.tooltipTitle}>{isCompare ? 'Closing Prices' : 'Closing Price'}</div>
          <div className={tStyles.tooltipPrices}>
            {priceEntries.map((entry) => (
              <div key={entry.dataKey} className={tStyles.tooltipPriceRow}>
                <span className={tStyles.tooltipTicker}>{entry.name || entry.dataKey}</span>
                <span>{formatPrice(entry.value)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function MarkerShape({ cx, cy, payload, onSelect }) {
  if (cx === undefined || cy === undefined || !payload?.eventId) {
    return null
  }

  const category = getEventCategory(payload.category)
  const radius = Math.max(5, Math.min(11, 4 + Number(payload.significance || 0) * 0.6))

  return (
    <g
      className={tStyles.chartMarker}
      onClick={() => onSelect(payload.eventId)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect(payload.eventId)
        }
      }}
    >
      <circle cx={cx} cy={cy} r={radius + 3} fill="rgba(8, 13, 26, 0.9)" />
      <circle cx={cx} cy={cy} r={radius + 1} fill={payload.tickerColor || '#818cf8'} opacity="0.4" />
      <circle cx={cx} cy={cy} r={radius - 1} fill={category.color} stroke={payload.tickerColor || '#818cf8'} strokeWidth={2} />
    </g>
  )
}

function EventCard({ event, selected, cardRef, tickerColor }) {
  const category = getEventCategory(event.category)

  return (
    <article
      ref={cardRef}
      className={`${tStyles.eventCard} ${selected ? tStyles.eventCardSelected : ''}`}
    >
      <div className={tStyles.eventTopRow}>
        <div className={tStyles.eventMeta}>
          <span className={tStyles.eventDate}>{formatDate(event.date)}</span>
          <span
            className={tStyles.eventCategory}
            style={{
              background: `${category.color}18`,
              borderColor: `${category.color}4d`,
              color: category.color,
            }}
          >
            {category.label}
          </span>
          <span className={tStyles.eventSignificance}>Significance {event.significance}</span>
        </div>
        <div className={tStyles.eventSourceRow}>
          {event.ticker ? (
            <span
              className={tStyles.eventTicker}
              style={{
                borderColor: `${tickerColor}66`,
                color: tickerColor,
              }}
            >
              {event.ticker}
            </span>
          ) : null}
          {event.source ? <span className={tStyles.eventSource}>{event.source}</span> : null}
        </div>
      </div>

      <h3 className={tStyles.eventTitle}>{event.title}</h3>
      {event.description ? <p className={tStyles.eventDescription}>{event.description}</p> : null}

      {(event.related_price?.close !== undefined || event.related_price?.change_pct !== undefined) ? (
        <div className={tStyles.eventPriceRow}>
          {event.related_price?.close !== undefined ? <span>{formatPrice(event.related_price.close)}</span> : null}
          {event.related_price?.change_pct !== undefined ? <span>{formatPercent(event.related_price.change_pct)}</span> : null}
        </div>
      ) : null}

      {event.source_url ? (
        <div className={tStyles.eventActions}>
          <a
            href={event.source_url}
            target="_blank"
            rel="noreferrer"
            className={tStyles.eventLink}
          >
            View Source
          </a>
        </div>
      ) : null}
    </article>
  )
}

export default function TimelinePage() {
  const router = useRouter()
  const eventRefs = useRef({})
  const requestIdRef = useRef(0)
  const highlightTimerRef = useRef(null)

  const [tickerInput, setTickerInput] = useState('')
  const [compareInput, setCompareInput] = useState('')
  const [yearsInput, setYearsInput] = useState(2)
  const [timeline, setTimeline] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedEventId, setSelectedEventId] = useState('')

  const fetchAndSetTimeline = useCallback(async ({ ticker, years, compare }) => {
    const normalizedTicker = normalizeTicker(ticker)
    const normalizedYears = normalizeYears(years)
    const compareState = parseCompareTickers(compare, normalizedTicker)
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId

    setLoading(true)
    setError('')
    setSelectedCategory('all')
    setSelectedEventId('')

    try {
      const payload = compareState.valid.length
        ? await fetchTimelineCompare({
            ticker: normalizedTicker,
            against: compareState.normalized,
            years: normalizedYears,
          })
        : await fetchTimeline({
            ticker: normalizedTicker,
            years: normalizedYears,
          })

      if (requestId !== requestIdRef.current) {
        return
      }

      const normalizedPayload = compareState.valid.length
        ? normalizeComparePayload(payload)
        : normalizeSinglePayload(payload)

      setTimeline(normalizedPayload)
      setTickerInput(normalizedTicker)
      setCompareInput(compareState.normalized)
      setYearsInput(normalizedYears)
    } catch (requestError) {
      if (requestId !== requestIdRef.current) {
        return
      }

      setTimeline(null)
      setError(requestError.message || 'Timeline request failed.')
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        clearTimeout(highlightTimerRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!router.isReady) {
      return
    }

    const queryTicker = normalizeTicker(router.query.ticker)
    const queryYears = normalizeYears(router.query.years)
    const rawCompare = typeof router.query.compare === 'string' ? router.query.compare : ''
    const compareState = parseCompareTickers(rawCompare, queryTicker)

    setTickerInput(queryTicker)
    setCompareInput(compareState.normalized)
    setYearsInput(queryYears)

    if (!queryTicker) {
      setTimeline(null)
      setError('')
      setLoading(false)
      setSelectedCategory('all')
      setSelectedEventId('')
      return
    }

    if (!TICKER_PATTERN.test(queryTicker)) {
      setTimeline(null)
      setLoading(false)
      setError('Enter a valid ticker symbol such as NVDA, AAPL, or MSFT.')
      return
    }

    if (rawCompare && !compareState.valid.length) {
      setTimeline(null)
      setLoading(false)
      setError('Enter at least one valid comparison ticker such as AMD or INTC.')
      return
    }

    fetchAndSetTimeline({
      ticker: queryTicker,
      years: queryYears,
      compare: compareState.normalized,
    })
  }, [fetchAndSetTimeline, router.isReady, router.query.compare, router.query.ticker, router.query.years])

  const handleRun = useCallback(async () => {
    const normalizedTicker = normalizeTicker(tickerInput)
    const normalizedYears = normalizeYears(yearsInput)
    const compareState = parseCompareTickers(compareInput, normalizedTicker)

    if (!normalizedTicker) {
      setTimeline(null)
      setError('Ticker is required.')
      return
    }

    if (!TICKER_PATTERN.test(normalizedTicker)) {
      setTimeline(null)
      setError('Enter a valid ticker symbol such as NVDA, AAPL, or MSFT.')
      return
    }

    if (compareInput && !compareState.valid.length) {
      setTimeline(null)
      setError('Enter at least one valid comparison ticker such as AMD or INTC.')
      return
    }

    const nextQuery = {
      ticker: normalizedTicker,
      years: normalizedYears,
    }

    if (compareState.valid.length) {
      nextQuery.compare = compareState.normalized
    }

    await router.push(
      {
        pathname: '/timeline',
        query: nextQuery,
      },
      undefined,
      { shallow: true }
    )
  }, [compareInput, router, tickerInput, yearsInput])

  const handleMarkerSelect = useCallback((eventId) => {
    setSelectedEventId(eventId)

    if (highlightTimerRef.current) {
      clearTimeout(highlightTimerRef.current)
    }

    const target = eventRefs.current[eventId]
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }

    highlightTimerRef.current = setTimeout(() => {
      setSelectedEventId((current) => (current === eventId ? '' : current))
    }, 2200)
  }, [])

  const timelineWarnings = useMemo(
    () => (Array.isArray(timeline?.warnings) ? timeline.warnings : []),
    [timeline]
  )

  const colorMap = useMemo(() => {
    const tickers = timeline?.tickers || []
    return tickers.reduce((accumulator, ticker, index) => {
      accumulator[ticker] = TICKER_COLORS[index % TICKER_COLORS.length]
      return accumulator
    }, {})
  }, [timeline])

  const sortedEvents = useMemo(() => {
    const rawEvents = Array.isArray(timeline?.events) ? timeline.events : []
    if (timeline?.mode === 'compare') {
      return rawEvents
    }

    return [...rawEvents].sort((left, right) => {
      if (left.date !== right.date) {
        return String(right.date || '').localeCompare(String(left.date || ''))
      }
      return Number(right.significance || 0) - Number(left.significance || 0)
    })
  }, [timeline])

  const availableCategories = useMemo(() => {
    const present = new Set(sortedEvents.map((event) => event.category).filter(Boolean))
    return CATEGORY_CONFIG.filter((item) => item.id === 'all' || present.has(item.id))
  }, [sortedEvents])

  const filteredEvents = useMemo(() => {
    if (selectedCategory === 'all') {
      return sortedEvents
    }

    return sortedEvents.filter((event) => event.category === selectedCategory)
  }, [selectedCategory, sortedEvents])

  const { chartRows, markerGroups } = useMemo(
    () => buildChartModel(timeline?.priceSeriesByTicker || {}, filteredEvents, timeline?.tickers || [], colorMap),
    [colorMap, filteredEvents, timeline]
  )

  const showPartialNotice = Boolean(timeline?.partial || timelineWarnings.length)
  const latestTicker = timeline?.titleTicker || normalizeTicker(router.query.ticker)
  const pageTitle = latestTicker ? `${latestTicker} Timeline` : 'Timeline'
  const isCompareMode = timeline?.mode === 'compare'
  const compareSummary = parseCompareTickers(compareInput, tickerInput)
  const statusMessages = [
    ...compareSummary.invalid.map((ticker) => `Ignored invalid comparison ticker: ${ticker}.`),
    ...(compareSummary.limitApplied ? [`Only the first ${MAX_COMPARE_TICKERS} comparison tickers will be used.`] : []),
  ]

  return (
    <>
      <Head>
        <title>{pageTitle} | Enterprise Intelligence</title>
      </Head>

      <main className={styles.page}>
        <section className={styles.hero}>
          <h1>Interactive Entity Timeline</h1>
          <p>
            Explore real stock-price history and grounded event chronology for one company or compare
            multiple tickers on the same timeline using the live backend timeline endpoints.
          </p>
        </section>

        <section className={styles.grid2}>
          <div className={styles.panel}>
            <h2>Timeline Request</h2>
            <div className={styles.controls}>
              <div className={tStyles.controlGrid}>
                <label className={styles.label}>
                  Primary Ticker
                  <input
                    className={styles.input}
                    value={tickerInput}
                    onChange={(event) => setTickerInput(normalizeTicker(event.target.value))}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !loading) {
                        handleRun()
                      }
                    }}
                    placeholder="NVDA"
                    autoComplete="off"
                  />
                </label>

                <label className={styles.label}>
                  Years
                  <select
                    className={styles.select}
                    value={yearsInput}
                    onChange={(event) => setYearsInput(normalizeYears(event.target.value))}
                  >
                    {YEAR_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className={styles.label}>
                Comparison Tickers
                <input
                  className={styles.input}
                  value={compareInput}
                  onChange={(event) => setCompareInput(normalizeCompareInput(event.target.value))}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !loading) {
                      handleRun()
                    }
                  }}
                  placeholder="AMD,INTC"
                  autoComplete="off"
                />
              </label>

              <div className={tStyles.compareHint}>
                Leave comparison tickers empty for single-company mode. When provided, the URL becomes
                shareable as <span className={styles.chip}>/timeline?ticker=NVDA&years=2&compare=AMD,INTC</span>.
              </div>

              {statusMessages.length ? (
                <div className={tStyles.compareMessages}>
                  {statusMessages.map((message) => (
                    <div key={message} className={tStyles.compareMessage}>
                      {message}
                    </div>
                  ))}
                </div>
              ) : null}

              <div className={styles.buttonRow}>
                <button className={styles.button} onClick={handleRun} disabled={loading}>
                  {loading ? 'Loading Timeline...' : isCompareMode || compareSummary.valid.length ? 'Compare Timelines' : 'View Timeline'}
                </button>
              </div>
            </div>
          </div>

          <div className={styles.panel}>
            <h2>Timeline Status</h2>
            {loading ? (
              <p className={styles.subtle}>Fetching live timeline, price series, and grounded events.</p>
            ) : error ? (
              <p className={styles.dangerText}>{error}</p>
            ) : timeline ? (
              <>
                <div className={styles.metaRow}>
                  <span className={styles.chip}>{timeline.entityName || timeline.titleTicker}</span>
                  {timeline.tickers.map((ticker) => (
                    <span key={ticker} className={styles.chip}>
                      {ticker}
                    </span>
                  ))}
                  <span className={styles.chip}>
                    {timeline.period?.start} to {timeline.period?.end}
                  </span>
                  <span className={styles.chip}>{timeline.summary?.total_events || 0} events</span>
                </div>
                <p className={styles.subtle}>
                  {isCompareMode
                    ? 'The chart overlays backend price series for all returned tickers and keeps merged backend event ordering.'
                    : 'The chart uses backend price_series, and the event cards use backend event IDs for marker navigation.'}
                </p>
              </>
            ) : (
              <p className={styles.empty}>Enter a valid ticker and load the real timeline.</p>
            )}
          </div>
        </section>

        {showPartialNotice ? (
          <section className={tStyles.notice}>
            <h2 className={tStyles.noticeTitle}>Partial timeline data returned</h2>
            <p className={tStyles.noticeText}>
              Some optional timeline sources were unavailable for this request. The usable grounded
              data below is still real and safe to inspect.
            </p>
            {timelineWarnings.length ? (
              <ul className={tStyles.warningList}>
                {timelineWarnings.map((warning, index) => (
                  <li key={`${warning.source || 'warning'}-${warning.code || index}`} className={tStyles.warningItem}>
                    <span className={tStyles.warningSource}>
                      {(warning.source || 'timeline').replace(/_/g, ' ')}
                    </span>
                    <span>{formatWarning(warning)}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ) : null}

        {timeline ? (
          <>
            <section className={tStyles.summaryGrid}>
              <div className={styles.panel}>
                <h3>Summary</h3>
                <div className={tStyles.kpiGrid}>
                  <div className={tStyles.kpiCard}>
                    <span className={tStyles.kpiLabel}>Primary Ticker</span>
                    <span className={tStyles.kpiValue}>{timeline.primaryTicker || '-'}</span>
                  </div>
                  <div className={tStyles.kpiCard}>
                    <span className={tStyles.kpiLabel}>{isCompareMode ? 'Compared Tickers' : 'Entity'}</span>
                    <span className={tStyles.kpiValue}>
                      {isCompareMode
                        ? timeline.compareTickers.length
                        : timeline.entityName || timeline.primaryTicker}
                    </span>
                  </div>
                  <div className={tStyles.kpiCard}>
                    <span className={tStyles.kpiLabel}>Events</span>
                    <span className={tStyles.kpiValue}>{formatNumber(timeline.summary?.total_events || 0)}</span>
                  </div>
                  <div className={tStyles.kpiCard}>
                    <span className={tStyles.kpiLabel}>Price Points</span>
                    <span className={tStyles.kpiValue}>
                      {formatNumber(
                        Object.values(timeline.priceSeriesByTicker || {}).reduce(
                          (total, points) => total + (Array.isArray(points) ? points.length : 0),
                          0
                        )
                      )}
                    </span>
                  </div>
                </div>

                {isCompareMode && timeline.tickers.length ? (
                  <div className={tStyles.tickerLegend}>
                    {timeline.tickers.map((ticker) => (
                      <span
                        key={ticker}
                        className={tStyles.tickerLegendItem}
                        style={{ borderColor: `${getTickerColor(ticker, colorMap)}66` }}
                      >
                        <span
                          className={tStyles.tickerLegendDot}
                          style={{ background: getTickerColor(ticker, colorMap) }}
                        />
                        {ticker}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </section>

            <section className={styles.panel}>
              <div className={tStyles.sectionHeader}>
                <div>
                  <h2 className={tStyles.sectionTitle}>Price Timeline and Event Overlay</h2>
                  <p className={tStyles.sectionText}>
                    {isCompareMode
                      ? 'Daily close from backend compare price series for each ticker with grounded event markers overlaid on the same chart.'
                      : 'Daily close from backend price_series with grounded event markers aligned by backend date and related price data where available.'}
                  </p>
                </div>
              </div>

              <div className={tStyles.filterRow}>
                {availableCategories.map((category) => {
                  const active = selectedCategory === category.id
                  return (
                    <button
                      key={category.id}
                      className={`${tStyles.filterPill} ${active ? tStyles.filterPillActive : ''}`}
                      style={active ? { borderColor: category.color, color: category.color } : undefined}
                      onClick={() => setSelectedCategory(category.id)}
                    >
                      {category.label}
                    </button>
                  )
                })}
              </div>

              <div className={tStyles.chartWrap}>
                {chartRows.length ? (
                  <ResponsiveContainer width="100%" height={380}>
                    <ComposedChart data={chartRows} margin={{ top: 20, right: 20, bottom: 10, left: 0 }}>
                      <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        minTickGap={28}
                        tickFormatter={(value) => formatDate(value)}
                      />
                      <YAxis
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        tickFormatter={(value) => formatPrice(value)}
                        width={88}
                      />
                      <Tooltip content={<TimelineTooltip isCompare={isCompareMode} />} />
                      {isCompareMode ? <Legend wrapperStyle={{ fontSize: '12px' }} /> : null}
                      {timeline.tickers.map((ticker, index) => {
                        const color = getTickerColor(ticker, colorMap)
                        if (isCompareMode) {
                          return (
                            <Line
                              key={`line-${ticker}`}
                              type="monotone"
                              dataKey={ticker}
                              name={ticker}
                              stroke={color}
                              strokeWidth={ticker === timeline.primaryTicker ? 2.8 : 2}
                              dot={false}
                              connectNulls
                              isAnimationActive={false}
                            />
                          )
                        }

                        return (
                          <Area
                            key={`area-${ticker}`}
                            type="monotone"
                            dataKey={ticker}
                            name={ticker}
                            stroke={color}
                            strokeWidth={2}
                            fill="rgba(99, 102, 241, 0.16)"
                            dot={false}
                            isAnimationActive={false}
                          />
                        )
                      })}
                      {timeline.tickers.map((ticker) => (
                        <Scatter
                          key={`scatter-${ticker}`}
                          data={markerGroups[ticker] || []}
                          dataKey="close"
                          name={`${ticker} Events`}
                          shape={(props) => <MarkerShape {...props} onSelect={handleMarkerSelect} />}
                          isAnimationActive={false}
                        />
                      ))}
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className={tStyles.emptyChart}>
                    No price series was available for this request.
                  </div>
                )}
              </div>

              <div className={tStyles.chartMeta}>
                <span>
                  {Object.values(markerGroups).reduce((total, markers) => total + markers.length, 0)} plotted markers
                </span>
                <span>{filteredEvents.length} visible events</span>
                {isCompareMode ? <span>{timeline.tickers.length} ticker series</span> : null}
              </div>
            </section>

            <section className={styles.panel}>
              <div className={tStyles.sectionHeader}>
                <div>
                  <h2 className={tStyles.sectionTitle}>Timeline Events</h2>
                  <p className={tStyles.sectionText}>
                    {isCompareMode
                      ? 'Merged backend event ordering across all returned tickers. Marker clicks scroll to the matching event card by backend event ID.'
                      : 'Newest first. Marker clicks scroll to the matching card using the backend event ID.'}
                  </p>
                </div>
              </div>

              {filteredEvents.length ? (
                <div className={tStyles.eventList}>
                  {filteredEvents.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      selected={selectedEventId === event.id}
                      tickerColor={getTickerColor(event.ticker, colorMap)}
                      cardRef={(node) => {
                        if (node) {
                          eventRefs.current[event.id] = node
                        } else {
                          delete eventRefs.current[event.id]
                        }
                      }}
                    />
                  ))}
                </div>
              ) : (
                <p className={styles.empty}>No events match the selected filter.</p>
              )}
            </section>
          </>
        ) : null}

        {!loading && !error && !timeline ? (
          <section className={styles.panel}>
            <p className={styles.empty}>
              Load a ticker to view the real entity timeline with stock price overlay, or add comparison tickers for multi-company mode.
            </p>
          </section>
        ) : null}
      </main>
    </>
  )
}
