import { useMemo, useState } from 'react'
import pageStyles from '../../src/styles/Page.module.css'
import styles from '../../src/styles/IntelligenceActivation.module.css'
import {
  EmptyState,
  formatCurrency,
  formatNumber,
  KeyValueGrid,
  Notice,
  PageHero,
  SectionCard,
  SimpleTable,
  SourceStatusGrid,
  WarningList,
} from '../../src/components/intelligence/ActivationShared'
import {
  fetchSelfDealingAnalysis,
  formatIntelligenceError,
  splitCommaSeparated,
} from '../../lib/intelligence'

const TICKER_PATTERN = /^[A-Z][A-Z0-9.-]{0,9}$/

const COMPANY_TICKER_ALIASES = {
  'NVIDIA': 'NVDA',
  'NVIDIA CORP': 'NVDA',
  'NVIDIA CORPORATION': 'NVDA',
  'APPLE': 'AAPL',
  'APPLE INC': 'AAPL',
  'APPLE INCORPORATED': 'AAPL',
  'MICROSOFT': 'MSFT',
  'MICROSOFT CORP': 'MSFT',
  'MICROSOFT CORPORATION': 'MSFT',
  'ALPHABET': 'GOOGL',
  'ALPHABET INC': 'GOOGL',
  'GOOGLE': 'GOOGL',
  'AMAZON': 'AMZN',
  'AMAZON COM': 'AMZN',
  'AMAZON.COM INC': 'AMZN',
  'TESLA': 'TSLA',
  'TESLA INC': 'TSLA',
}

function normalizeTickerInput(ticker, entityName = '') {
  const raw = String(ticker || '').trim().toUpperCase()
  if (!raw) {
    return ''
  }
  if (TICKER_PATTERN.test(raw)) {
    return raw
  }
  const clean = raw.replace(/[^A-Z0-9]+/g, ' ').replace(/\s+/g, ' ').trim()
  const entityClean = String(entityName || '').toUpperCase().replace(/[^A-Z0-9]+/g, ' ').replace(/\s+/g, ' ').trim()
  return COMPANY_TICKER_ALIASES[clean] || COMPANY_TICKER_ALIASES[entityClean] || raw
}

function SelfDealingState({ result, error, loading }) {
  if (loading) {
    return <Notice tone="info" title="Running grounded self-dealing analysis">Checking proxy disclosures, insider relationships, board interlocks, contract references, and available holder/family inputs.</Notice>
  }

  if (error) {
    const parsed = formatIntelligenceError(error)
    return <Notice tone={parsed.status >= 500 || parsed.status === 0 ? 'error' : 'warn'} title={parsed.status ? `Request error (${parsed.status})` : 'Request error'}>{parsed.detail || parsed.message}</Notice>
  }

  if (!result) {
    return <Notice tone="info" title="Ready">Submit an entity to review only grounded disclosures and corroborating source overlap.</Notice>
  }

  const findings = result.analysis?.findings || []
  if (!findings.length && result.partial) {
    return <Notice tone="warn" title="No corroborated findings, but source coverage was partial">The backend returned no suspicious corroboration, but one or more supporting sources were unavailable or incomplete for this run.</Notice>
  }
  if (!findings.length) {
    return <Notice tone="success" title="No suspicious findings">No corroborated self-dealing indicators were returned for the submitted inputs.</Notice>
  }
  return <Notice tone="success" title="Grounded findings returned">The result includes corroborated overlap findings only. Review the evidence and warnings below before drawing conclusions.</Notice>
}

export default function SelfDealingPage() {
  const [form, setForm] = useState({
    entity_name: '',
    ticker: '',
    related_entities: '',
    include_family_network: true,
    include_institutional_holders: true,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const findings = result?.analysis?.findings || []
  const unmatched = result?.analysis?.unmatched || []
  const summary = result?.analysis?.summary || {}
  const inputsAvailable = result?.analysis?.inputs_available || {}

  const findingRows = useMemo(() => (
    findings.map((finding, index) => ({
      id: `${finding.counterparty || index}-${index}`,
      ...finding,
    }))
  ), [findings])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (loading) {
      return
    }
    if (!form.entity_name.trim()) {
      setError({ status: 400, message: 'Entity name is required.', detail: 'entity_name: field required', raw: null })
      setResult(null)
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const normalizedTicker = normalizeTickerInput(form.ticker, form.entity_name)
      if (normalizedTicker && !TICKER_PATTERN.test(normalizedTicker)) {
        setError({
          status: 400,
          message: 'Ticker must be a stock symbol.',
          detail: 'Enter a ticker symbol such as NVDA, AAPL, or MSFT. Do not enter the full company name in the ticker field.',
          raw: null,
        })
        setLoading(false)
        return
      }
      if (normalizedTicker !== form.ticker.trim().toUpperCase()) {
        setForm((current) => ({ ...current, ticker: normalizedTicker }))
      }
      const payload = {
        entity_name: form.entity_name.trim(),
        ticker: normalizedTicker,
        related_entities: splitCommaSeparated(form.related_entities),
        include_family_network: form.include_family_network,
        include_institutional_holders: form.include_institutional_holders,
      }
      const response = await fetchSelfDealingAnalysis(payload)
      setResult(response)
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setForm({
      entity_name: '',
      ticker: '',
      related_entities: '',
      include_family_network: true,
      include_institutional_holders: true,
    })
    setResult(null)
    setError(null)
    setLoading(false)
  }

  return (
    <div className={styles.page}>
      <PageHero
        title="Self-Dealing Analysis"
        description="Run the grounded self-dealing workflow against the current intelligence activation backend. This page only surfaces corroborated disclosure overlap, source availability, warnings, and no-findings states returned by the service."
      />

      <div className={styles.layout}>
        <section className={styles.panel}>
          <h2 className={styles.panelTitle}>Request</h2>
          <form className={styles.form} onSubmit={handleSubmit}>
            <label className={styles.label}>
              Entity Name
              <input
                className={styles.input}
                value={form.entity_name}
                onChange={(event) => setForm((current) => ({ ...current, entity_name: event.target.value }))}
                placeholder="Example Corp"
              />
            </label>

            <label className={styles.label}>
              Ticker
              <input
                className={styles.input}
                value={form.ticker}
                onChange={(event) => setForm((current) => ({ ...current, ticker: event.target.value.toUpperCase() }))}
                onBlur={() => setForm((current) => ({ ...current, ticker: normalizeTickerInput(current.ticker, current.entity_name) }))}
                placeholder="NVDA"
              />
              <span className={styles.helpText}>Use the stock symbol only. Example: NVDA, AAPL, MSFT.</span>
            </label>

            <label className={styles.label}>
              Related Entities
              <input
                className={styles.input}
                value={form.related_entities}
                onChange={(event) => setForm((current) => ({ ...current, related_entities: event.target.value }))}
                placeholder="Acme Ventures LLC, Example Family Office"
              />
              <span className={styles.helpText}>Comma-separated values map directly to the backend related_entities list.</span>
            </label>

            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={form.include_family_network}
                onChange={(event) => setForm((current) => ({ ...current, include_family_network: event.target.checked }))}
              />
              Include family network analysis
            </label>

            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={form.include_institutional_holders}
                onChange={(event) => setForm((current) => ({ ...current, include_institutional_holders: event.target.checked }))}
              />
              Include institutional holder analysis
            </label>

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.button} disabled={loading}>
                {loading ? 'Running...' : 'Run Self-Dealing Analysis'}
              </button>
              <button type="button" className={`${styles.button} ${styles.secondaryButton}`} onClick={handleReset} disabled={loading}>
                Reset
              </button>
            </div>
          </form>
        </section>

        <div className={styles.results}>
          <SelfDealingState result={result} error={error} loading={loading} />

          {result ? (
            <>
              <SectionCard title="Run Summary" aside={result.partial ? <span className={`${styles.pill} ${styles.pillMedium}`}>Partial</span> : <span className={`${styles.pill} ${styles.pillLow}`}>Complete</span>}>
                <KeyValueGrid
                  items={[
                    { label: 'Entity', value: result.entity_name || '-' },
                    { label: 'Ticker', value: result.ticker || '-' },
                    { label: 'CIK', value: result.cik || '-' },
                    { label: 'Transactions examined', value: formatNumber(summary.transactions_examined) },
                    { label: 'Transactions corroborated', value: formatNumber(summary.transactions_corroborated) },
                    { label: 'Risk level', value: summary.risk_level || 'NONE' },
                    { label: 'Largest corroborated amount', value: formatCurrency(summary.largest_corroborated_amount) },
                    { label: 'Board-seat matches', value: formatNumber(summary.board_seat_matches) },
                    { label: 'Federal counterparty matches', value: formatNumber(summary.federal_counterparty_matches) },
                    { label: 'Insider surname matches', value: formatNumber(summary.insider_surname_matches) },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Source Availability">
                <SourceStatusGrid sourceStatus={result.source_status} />
              </SectionCard>

              <SectionCard title="Input Coverage">
                <KeyValueGrid
                  items={Object.entries(inputsAvailable).map(([key, value]) => ({
                    label: key.replace(/_/g, ' '),
                    value: value ? 'Available' : 'Not returned',
                  }))}
                />
              </SectionCard>

              <SectionCard title="Findings">
                {findingRows.length ? (
                  <SimpleTable
                    columns={[
                      { key: 'counterparty', label: 'Counterparty' },
                      { key: 'score', label: 'Score', numeric: true },
                      { key: 'amount', label: 'Amount', numeric: true, render: (row) => formatCurrency(row.amount) },
                      { key: 'evidence', label: 'Evidence', render: (row) => (
                        <ul className={styles.list}>
                          {(row.evidence || []).map((item, index) => (
                            <li key={`${item.type || 'evidence'}-${index}`}>{item.detail || item.type || 'Evidence returned.'}</li>
                          ))}
                        </ul>
                      ) },
                    ]}
                    rows={findingRows}
                  />
                ) : (
                  <EmptyState>No corroborated findings were returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Unmatched Disclosures">
                {unmatched.length ? (
                  <SimpleTable
                    columns={[
                      { key: 'counterparty', label: 'Counterparty' },
                      { key: 'amount', label: 'Amount', numeric: true, render: (row) => formatCurrency(row.amount) },
                      { key: 'detail', label: 'Detail', render: (row) => row.detail || row.reason || '-' },
                    ]}
                    rows={unmatched}
                  />
                ) : (
                  <EmptyState>No unmatched disclosures were returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Warnings">
                <WarningList warnings={result.warnings || []} />
              </SectionCard>
            </>
          ) : (
            <section className={styles.section}>
              <div className={pageStyles.empty}>Results will appear here after a successful run.</div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
