import Head from 'next/head'
import { useEffect, useRef, useState } from 'react'
import { fetchInstitutionalExposure } from '../../lib/institutional'
import { EXPOSURE_DEFAULTS } from '../../lib/institutional-models'
import styles from '../../src/styles/Page.module.css'
import sectionStyles from '../../src/styles/Institutional.module.css'

const EMPTY = 'N/A'

const INITIAL_FORM = {
  institution_cik: '',
  q: '',
  ticker: '',
  cusip: '',
  report_period: '',
  limit: String(EXPOSURE_DEFAULTS.limit),
  offset: String(EXPOSURE_DEFAULTS.offset),
}

function formatErrorDetail(detail) {
  if (Array.isArray(detail)) {
    return detail.map((item, index) => {
      if (typeof item === 'string') {
        return <li key={index}>{item}</li>
      }

      if (item && typeof item === 'object') {
        const location = Array.isArray(item.loc) ? item.loc.join('.') : item.loc
        const message = item.msg || JSON.stringify(item)
        return <li key={index}>{location ? `${location}: ${message}` : message}</li>
      }

      return <li key={index}>{String(item)}</li>
    })
  }

  if (detail && typeof detail === 'object') {
    return <li>{detail.message || JSON.stringify(detail, null, 2)}</li>
  }

  return <li>{String(detail || 'Request failed.')}</li>
}

function formatDate(value) {
  if (!value) {
    return EMPTY
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatNumber(value, options = {}) {
  if (value === null || value === undefined || value === '') {
    return EMPTY
  }

  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) {
    return String(value)
  }

  return numericValue.toLocaleString('en-US', options)
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === '') {
    return EMPTY
  }

  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) {
    return String(value)
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(numericValue)
}

function ExposureTable({ results }) {
  if (!results || results.length === 0) {
    return (
      <p className={styles.empty}>
        No grounded institutional exposure data was found for these filters.
      </p>
    )
  }

  return (
    <div className={sectionStyles.tableWrap}>
      <table className={sectionStyles.table}>
        <thead>
          <tr>
            <th>Manager</th>
            <th>CIK</th>
            <th>Issuer / Security</th>
            <th>Ticker</th>
            <th>CUSIP</th>
            <th>Reported Value</th>
            <th>Shares</th>
            <th>Report Period</th>
            <th>Filing</th>
          </tr>
        </thead>
        <tbody>
          {results.map((item, index) => (
            <tr key={`${item.institution_cik || 'cik'}-${item.cusip || item.issuer_name || index}-${item.report_period || index}`}>
              <td className={sectionStyles.issuerCell}>
                <span>{item.institution_name || EMPTY}</span>
                <span className={sectionStyles.cellSubtle}>{item.accession_number || EMPTY}</span>
              </td>
              <td>{item.institution_cik || EMPTY}</td>
              <td className={sectionStyles.issuerCell}>
                <span>{item.issuer_name || EMPTY}</span>
                <span className={sectionStyles.cellSubtle}>{item.security_title || EMPTY}</span>
              </td>
              <td>{item.ticker || EMPTY}</td>
              <td>{item.cusip || EMPTY}</td>
              <td>{formatCurrency(item.reported_value_usd)}</td>
              <td>{formatNumber(item.shares, { maximumFractionDigits: 0 })}</td>
              <td>{formatDate(item.report_period)}</td>
              <td>{formatDate(item.filing_date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function InstitutionalExposurePage() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [response, setResponse] = useState(null)
  const requestIdRef = useRef(0)
  const mountedRef = useRef(true)

  useEffect(() => {
    return () => {
      mountedRef.current = false
    }
  }, [])

  const updateField = (key) => (event) => {
    setForm((current) => ({ ...current, [key]: event.target.value }))
  }

  const hasAnyFilter = () => (
    form.institution_cik.trim()
    || form.q.trim()
    || form.ticker.trim()
    || form.cusip.trim()
    || form.report_period
  )

  const submitSearch = async (event, nextOffset = null) => {
    event?.preventDefault()
    if (loading) {
      return
    }

    if (!hasAnyFilter()) {
      setError({
        status: 0,
        detail: 'Enter at least one grounded exposure filter.',
        message: 'Enter at least one grounded exposure filter.',
        raw: null,
      })
      setResponse(null)
      return
    }

    const limit = Math.min(Math.max(Number(form.limit) || EXPOSURE_DEFAULTS.limit, 1), 500)
    const offset = Math.max((nextOffset ?? Number(form.offset)) || 0, 0)
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const payload = await fetchInstitutionalExposure({
        institution_cik: form.institution_cik.trim(),
        q: form.q.trim(),
        ticker: form.ticker.trim(),
        cusip: form.cusip.trim(),
        report_period: form.report_period,
        limit,
        offset,
      })

      if (mountedRef.current && requestIdRef.current === requestId) {
        setForm((current) => ({ ...current, limit: String(limit), offset: String(offset) }))
        setResponse(payload)
      }
    } catch (requestError) {
      if (mountedRef.current && requestIdRef.current === requestId) {
        setError({
          status: requestError.status || 0,
          detail: requestError.detail || requestError.message,
          message: requestError.message || 'Request failed.',
          raw: requestError.raw || null,
        })
      }
    } finally {
      if (mountedRef.current && requestIdRef.current === requestId) {
        setLoading(false)
      }
    }
  }

  const resetSearch = () => {
    if (loading) {
      return
    }

    requestIdRef.current += 1
    setForm(INITIAL_FORM)
    setError(null)
    setResponse(null)
  }

  const pagination = response?.pagination
  const canGoBack = Number(pagination?.offset || 0) > 0
  const canGoForward = pagination
    ? Number(pagination.offset || 0) + Number(pagination.returned || 0) < Number(pagination.total_matching || 0)
    : false

  return (
    <>
      <Head>
        <title>Institutional Exposure Search</title>
        <meta
          name="description"
          content="Search real cached 13F institutional exposure by manager, issuer, ticker, CUSIP, and reporting period."
        />
      </Head>
      <main className={styles.page}>
        <section className={styles.hero}>
          <h1>Institutional Exposure Search</h1>
          <p>
            Search grounded 13F cache records by manager CIK, issuer, ticker, CUSIP, or reporting
            period. Results come only from persisted SEC-derived 13F data.
          </p>
        </section>

        <section className={styles.panel}>
          <h2>Search Exposure</h2>
          <form className={styles.controls} onSubmit={submitSearch}>
            <div className={sectionStyles.formGrid}>
              <label className={styles.label}>
                Institution CIK
                <input
                  className={styles.input}
                  value={form.institution_cik}
                  onChange={updateField('institution_cik')}
                  placeholder="e.g. 1067983"
                  disabled={loading}
                />
              </label>
              <label className={styles.label}>
                Issuer / Security Query
                <input
                  className={styles.input}
                  value={form.q}
                  onChange={updateField('q')}
                  placeholder="e.g. Apple"
                  disabled={loading}
                />
              </label>
              <label className={styles.label}>
                Ticker
                <input
                  className={styles.input}
                  value={form.ticker}
                  onChange={updateField('ticker')}
                  placeholder="e.g. AAPL"
                  disabled={loading}
                />
              </label>
              <label className={styles.label}>
                CUSIP
                <input
                  className={styles.input}
                  value={form.cusip}
                  onChange={updateField('cusip')}
                  placeholder="Optional"
                  disabled={loading}
                />
              </label>
              <label className={styles.label}>
                Reporting Period
                <input
                  className={styles.input}
                  type="date"
                  value={form.report_period}
                  onChange={updateField('report_period')}
                  disabled={loading}
                />
              </label>
              <label className={styles.label}>
                Limit
                <input
                  className={styles.input}
                  type="number"
                  min="1"
                  max="500"
                  value={form.limit}
                  onChange={updateField('limit')}
                  disabled={loading}
                />
              </label>
              <label className={styles.label}>
                Offset
                <input
                  className={styles.input}
                  type="number"
                  min="0"
                  value={form.offset}
                  onChange={updateField('offset')}
                  disabled={loading}
                />
              </label>
            </div>
            <div className={styles.buttonRow}>
              <button className={styles.button} type="submit" disabled={loading}>
                {loading ? 'Searching...' : 'Search'}
              </button>
              <button className={styles.button} type="button" onClick={resetSearch} disabled={loading}>
                Reset
              </button>
            </div>
            <p className={styles.subtle}>
              Enter at least one filter. This page does not perform person-level search or show demo rows.
            </p>
          </form>
        </section>

        {error ? (
          <section className={styles.panel}>
            <h2>Request Error</h2>
            <p className={styles.dangerText}>
              {error.status ? `HTTP ${error.status}` : 'Validation error'}
            </p>
            <ul className={sectionStyles.errorList}>{formatErrorDetail(error.detail)}</ul>
            {error.raw ? <pre className={styles.mono}>{JSON.stringify(error.raw, null, 2)}</pre> : null}
          </section>
        ) : null}

        {loading ? (
          <section className={styles.panel}>
            <h2>Loading</h2>
            <p className={styles.subtle}>Searching cached institutional 13F exposure...</p>
          </section>
        ) : null}

        {response ? (
          <div className={sectionStyles.sectionStack}>
            <section className={styles.panel}>
              <h2>Results</h2>
              <div className={styles.metaRow}>
                <span className={styles.chip}>Returned: {formatNumber(pagination?.returned)}</span>
                <span className={styles.chip}>Total: {formatNumber(pagination?.total_matching)}</span>
                <span className={styles.chip}>Limit: {formatNumber(pagination?.limit)}</span>
                <span className={styles.chip}>Offset: {formatNumber(pagination?.offset)}</span>
                <span className={styles.chip}>Source: {response.data_source || EMPTY}</span>
              </div>
            </section>

            <section className={styles.panel}>
              <h2>Institutional Exposure</h2>
              <ExposureTable results={response.results} />
            </section>

            <section className={styles.panel}>
              <h2>Pagination</h2>
              <div className={styles.buttonRow}>
                <button
                  className={styles.button}
                  type="button"
                  disabled={!canGoBack || loading}
                  onClick={() => submitSearch(null, Math.max(Number(pagination?.offset || 0) - Number(pagination?.limit || EXPOSURE_DEFAULTS.limit), 0))}
                >
                  Previous
                </button>
                <button
                  className={styles.button}
                  type="button"
                  disabled={!canGoForward || loading}
                  onClick={() => submitSearch(null, Number(pagination?.offset || 0) + Number(pagination?.limit || EXPOSURE_DEFAULTS.limit))}
                >
                  Next
                </button>
              </div>
            </section>
          </div>
        ) : null}
      </main>
    </>
  )
}
