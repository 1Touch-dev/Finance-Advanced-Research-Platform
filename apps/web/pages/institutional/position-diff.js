import Head from 'next/head'
import { useEffect, useRef, useState } from 'react'
import { fetchInstitutionalPositionDiff } from '../../lib/institutional'
import {
  POSITION_DIFF_DATA_QUALITY_LABELS,
  POSITION_DIFF_DEFAULTS,
  POSITION_DIFF_HIGHLIGHT_LABELS,
  POSITION_DIFF_SECTION_LABELS,
  POSITION_DIFF_STATUS_LABELS,
} from '../../lib/institutional-models'
import styles from '../../src/styles/Page.module.css'
import sectionStyles from '../../src/styles/Institutional.module.css'

const INITIAL_FORM = {
  institution_cik: '',
  current_period: '',
  previous_period: '',
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
    return '—'
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
    return '—'
  }

  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) {
    return String(value)
  }

  return numericValue.toLocaleString('en-US', options)
}

function formatCurrency(value) {
  if (value === null || value === undefined) {
    return '—'
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

function DetailList({ items }) {
  const populated = items.filter((item) => item.value !== null && item.value !== undefined && item.value !== '')

  if (populated.length === 0) {
    return <p className={styles.empty}>No details available.</p>
  }

  return (
    <dl className={sectionStyles.detailList}>
      {populated.map((item) => (
        <div key={item.label} className={sectionStyles.detailRow}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

function SummaryGrid({ summary }) {
  const items = [
    { label: 'Current Positions', value: formatNumber(summary?.current_position_count) },
    { label: 'Previous Positions', value: formatNumber(summary?.previous_position_count) },
    { label: 'New', value: formatNumber(summary?.new_count) },
    { label: 'Increased', value: formatNumber(summary?.increased_count) },
    { label: 'Reduced', value: formatNumber(summary?.reduced_count) },
    { label: 'Exited', value: formatNumber(summary?.exited_count) },
    { label: 'Total Value Difference', value: formatCurrency(summary?.total_reported_value_diff_usd) },
  ]

  return (
    <div className={sectionStyles.metricGrid}>
      {items.map((item) => (
        <div key={item.label} className={sectionStyles.metricCard}>
          <span className={sectionStyles.metricValue}>{item.value}</span>
          <span className={sectionStyles.metricLabel}>{item.label}</span>
        </div>
      ))}
    </div>
  )
}

function DataQualityList({ dataQuality }) {
  const items = Object.entries(POSITION_DIFF_DATA_QUALITY_LABELS).map(([key, label]) => ({
    key,
    label,
    value: Boolean(dataQuality?.[key]),
  }))

  return (
    <div className={sectionStyles.flagList}>
      {items.map((item) => (
        <div key={item.key} className={sectionStyles.flagRow}>
          <span className={sectionStyles.flagLabel}>{item.label}</span>
          <span
            className={
              item.value
                ? `${sectionStyles.flagBadge} ${sectionStyles.flagBadgeOk}`
                : `${sectionStyles.flagBadge} ${sectionStyles.flagBadgeWarn}`
            }
          >
            {item.value ? 'Yes' : 'No'}
          </span>
        </div>
      ))}
    </div>
  )
}

function WarningList({ warnings }) {
  if (!warnings || warnings.length === 0) {
    return <p className={styles.empty}>No warnings returned.</p>
  }

  return (
    <div className={sectionStyles.warningList}>
      {warnings.map((warning, index) => (
        <div
          key={`${warning.code || 'warning'}-${warning.key || index}`}
          className={sectionStyles.warningCard}
        >
          <div className={sectionStyles.warningHeader}>
            <span className={sectionStyles.warningCode}>{warning.code || 'warning'}</span>
            {warning.key ? <span className={sectionStyles.warningKey}>{warning.key}</span> : null}
          </div>
          <p className={sectionStyles.warningMessage}>{warning.message}</p>
        </div>
      ))}
    </div>
  )
}

function PositionList({ title, positions, emptyMessage }) {
  return (
    <section className={styles.panel}>
      <h2>{title}</h2>
      {!positions || positions.length === 0 ? (
        <p className={styles.empty}>{emptyMessage}</p>
      ) : (
        <div className={sectionStyles.highlightGrid}>
          {positions.map((position) => (
            <article
              key={`${title}-${position.issuer_name}-${position.cusip || position.current_accession_number || position.previous_accession_number || 'na'}`}
              className={sectionStyles.highlightCard}
            >
              <div className={sectionStyles.highlightTop}>
                <h3>{position.issuer_name}</h3>
                <span className={sectionStyles.statusBadge}>
                  {POSITION_DIFF_STATUS_LABELS[position.status] || position.status}
                </span>
              </div>
              <div className={sectionStyles.highlightMeta}>
                <span>{position.ticker || 'No ticker'}</span>
                <span>{position.cusip || 'No CUSIP'}</span>
              </div>
              <div className={sectionStyles.highlightNumbers}>
                <span>Shares: {formatNumber(position.share_diff)}</span>
                <span>Value: {formatCurrency(position.reported_value_diff_usd)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function FilingInfo({ filings }) {
  const current = filings?.current
  const previous = filings?.previous

  return (
    <div className={sectionStyles.filingGrid}>
      <div className={sectionStyles.filingCard}>
        <h3>Current Filing</h3>
        <DetailList
          items={[
            { label: 'Accession Number', value: current?.accession_number || '—' },
            { label: 'Filing Date', value: formatDate(current?.filing_date) },
            { label: 'Form', value: current?.form || '—' },
          ]}
        />
      </div>
      <div className={sectionStyles.filingCard}>
        <h3>Previous Filing</h3>
        <DetailList
          items={[
            { label: 'Accession Number', value: previous?.accession_number || '—' },
            { label: 'Filing Date', value: formatDate(previous?.filing_date) },
            { label: 'Form', value: previous?.form || '—' },
          ]}
        />
      </div>
    </div>
  )
}

function PositionDifferencesTable({ positions }) {
  if (!positions || positions.length === 0) {
    return <p className={styles.empty}>No position differences matched this request.</p>
  }

  return (
    <div className={sectionStyles.tableWrap}>
      <table className={sectionStyles.table}>
        <thead>
          <tr>
            <th>Issuer</th>
            <th>Ticker</th>
            <th>CUSIP</th>
            <th>Current Shares</th>
            <th>Previous Shares</th>
            <th>Share Difference</th>
            <th>Value Difference</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr
              key={`${position.issuer_name}-${position.cusip || position.current_accession_number || position.previous_accession_number || position.status}`}
            >
              <td className={sectionStyles.issuerCell}>
                <span>{position.issuer_name}</span>
                {position.security_title ? (
                  <span className={sectionStyles.cellSubtle}>{position.security_title}</span>
                ) : null}
              </td>
              <td>{position.ticker || '—'}</td>
              <td>{position.cusip || '—'}</td>
              <td>{formatNumber(position.current_shares, { maximumFractionDigits: 0 })}</td>
              <td>{formatNumber(position.previous_shares, { maximumFractionDigits: 0 })}</td>
              <td>{formatNumber(position.share_diff, { maximumFractionDigits: 0 })}</td>
              <td>{formatCurrency(position.reported_value_diff_usd)}</td>
              <td>
                <span className={sectionStyles.statusBadge}>
                  {POSITION_DIFF_STATUS_LABELS[position.status] || position.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function InstitutionalPositionDiffPage() {
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

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (loading) {
      return
    }

    const institutionCik = form.institution_cik.trim()
    if (!institutionCik) {
      setError({
        status: 0,
        detail: 'Institution CIK is required.',
        message: 'Institution CIK is required.',
        raw: null,
      })
      setResponse(null)
      return
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const payload = await fetchInstitutionalPositionDiff({
        institution_cik: institutionCik,
        current_period: form.current_period,
        previous_period: form.previous_period,
        status: POSITION_DIFF_DEFAULTS.status,
        sort_by: POSITION_DIFF_DEFAULTS.sortBy,
        sort_dir: POSITION_DIFF_DEFAULTS.sortDir,
        limit: POSITION_DIFF_DEFAULTS.limit,
        offset: POSITION_DIFF_DEFAULTS.offset,
      })
      if (mountedRef.current && requestIdRef.current === requestId) {
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

  const handleReset = () => {
    if (loading) {
      return
    }

    setForm(INITIAL_FORM)
    setError(null)
    setResponse(null)
  }

  return (
    <>
      <Head>
        <title>Institutional Position Difference</title>
        <meta
          name="description"
          content="Compare quarter-over-quarter Form 13F position changes for an institutional manager."
        />
      </Head>
      <main className={styles.page}>
        <section className={styles.hero}>
          <h1>Institutional Position Difference</h1>
          <p>
            Compare consecutive 13F reporting periods for a manager and inspect filing provenance,
            summary counts, warnings, quality flags, and position-level changes.
          </p>
        </section>

        <section className={styles.panel}>
          <h2>Compare 13F Periods</h2>
          <form className={styles.controls} onSubmit={handleSubmit}>
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
                Current Period
                <input
                  className={styles.input}
                  type="date"
                  value={form.current_period}
                  onChange={updateField('current_period')}
                  disabled={loading}
                />
              </label>
              <label className={styles.label}>
                Previous Period
                <input
                  className={styles.input}
                  type="date"
                  value={form.previous_period}
                  onChange={updateField('previous_period')}
                  disabled={loading}
                />
              </label>
            </div>
            <div className={styles.buttonRow}>
              <button className={styles.button} type="submit" disabled={loading}>
                {loading ? 'Comparing...' : 'Compare'}
              </button>
              <button className={styles.button} type="button" onClick={handleReset} disabled={loading}>
                Reset
              </button>
            </div>
            <p className={styles.subtle}>
              Required: institution CIK. Optional: current and previous quarter-end dates.
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
            {error.raw ? (
              <pre className={styles.mono}>{JSON.stringify(error.raw, null, 2)}</pre>
            ) : null}
          </section>
        ) : null}

        {loading ? (
          <section className={styles.panel}>
            <h2>Loading</h2>
            <p className={styles.subtle}>Fetching institutional 13F position difference data...</p>
          </section>
        ) : null}

        {response ? (
          <div className={sectionStyles.sectionStack}>
            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.institution}</h2>
              <DetailList
                items={[
                  { label: 'Name', value: response.institution?.name || '—' },
                  { label: 'CIK', value: response.institution?.cik || '—' },
                ]}
              />
            </section>

            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.periods}</h2>
              <DetailList
                items={[
                  { label: 'Current Period', value: formatDate(response.periods?.current) },
                  { label: 'Previous Period', value: formatDate(response.periods?.previous) },
                ]}
              />
            </section>

            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.filings}</h2>
              <FilingInfo filings={response.filings} />
            </section>

            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.summary}</h2>
              <SummaryGrid summary={response.summary} />
            </section>

            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.dataQuality}</h2>
              <DataQualityList dataQuality={response.data_quality} />
            </section>

            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.warnings}</h2>
              <WarningList warnings={response.warnings} />
            </section>

            <PositionList
              title={POSITION_DIFF_HIGHLIGHT_LABELS.largest_buyers}
              positions={response.highlights?.largest_buyers}
              emptyMessage="No largest buyers returned."
            />
            <PositionList
              title={POSITION_DIFF_HIGHLIGHT_LABELS.largest_sellers}
              positions={response.highlights?.largest_sellers}
              emptyMessage="No largest sellers returned."
            />
            <PositionList
              title={POSITION_DIFF_HIGHLIGHT_LABELS.new_positions}
              positions={response.highlights?.new_positions}
              emptyMessage="No new positions returned."
            />
            <PositionList
              title={POSITION_DIFF_HIGHLIGHT_LABELS.complete_exits}
              positions={response.highlights?.complete_exits}
              emptyMessage="No complete exits returned."
            />

            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.positions}</h2>
              <PositionDifferencesTable positions={response.positions} />
            </section>

            <section className={styles.panel}>
              <h2>{POSITION_DIFF_SECTION_LABELS.pagination}</h2>
              <DetailList
                items={[
                  { label: 'Returned', value: formatNumber(response.pagination?.returned) },
                  { label: 'Total Matching', value: formatNumber(response.pagination?.total_matching) },
                  { label: 'Limit', value: formatNumber(response.pagination?.limit) },
                  { label: 'Offset', value: formatNumber(response.pagination?.offset) },
                ]}
              />
            </section>
          </div>
        ) : null}
      </main>
    </>
  )
}
