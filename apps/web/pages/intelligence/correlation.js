import { useState } from 'react'
import styles from '../../src/styles/IntelligenceActivation.module.css'
import {
  EmptyState,
  formatCurrency,
  formatNumber,
  formatPercent,
  KeyValueGrid,
  Notice,
  PageHero,
  SectionCard,
  SimpleTable,
  SourceStatusGrid,
  WarningList,
} from '../../src/components/intelligence/ActivationShared'
import {
  fetchCorrelationAnalysis,
  formatIntelligenceError,
  splitCommaSeparated,
} from '../../lib/intelligence'

function ResultState({ result, error, loading }) {
  if (loading) {
    return <Notice tone="info" title="Running grounded correlation analysis">Checking insider timing, price history, event studies, political and contract relationships, and optional comparative analysis.</Notice>
  }
  if (error) {
    const parsed = formatIntelligenceError(error)
    return <Notice tone={parsed.status >= 500 || parsed.status === 0 ? 'error' : 'warn'} title={parsed.status ? `Request error (${parsed.status})` : 'Request error'}>{parsed.detail || parsed.message}</Notice>
  }
  if (!result) {
    return <Notice tone="info" title="Ready">Submit an entity to review the grounded correlation and comparative output already supported by the backend.</Notice>
  }
  if (!result.correlations || Object.keys(result.correlations).length === 0) {
    return <Notice tone={result.partial ? 'warn' : 'success'} title={result.partial ? 'Partial data returned' : 'No correlation signals returned'}>{result.partial ? 'One or more upstream providers were unavailable, so only partial analysis could be returned.' : 'The backend returned no grounded correlation or event-study signals for this request.'}</Notice>
  }
  return <Notice tone="success" title="Grounded correlation data returned">Only grounded provider output and clearly labeled unavailable states are shown below.</Notice>
}

export default function CorrelationPage() {
  const [form, setForm] = useState({
    entity_name: '',
    ticker: '',
    competitors: '',
    years: 2,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const correlations = result?.correlations || {}
  const deepComparative = result?.deep_comparative || {}
  const eventReturns = correlations.event_returns || {}
  const insiderTiming = correlations.insider_timing || {}
  const lobbyingLag = correlations.lobbying_lag || {}
  const contractPolitical = correlations.contract_political || {}

  const onSubmit = async (event) => {
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
      const response = await fetchCorrelationAnalysis({
        entity_name: form.entity_name.trim(),
        ticker: form.ticker.trim().toUpperCase(),
        competitors: splitCommaSeparated(form.competitors),
        years: Number(form.years),
      })
      setResult(response)
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  const onReset = () => {
    setForm({
      entity_name: '',
      ticker: '',
      competitors: '',
      years: 2,
    })
    setResult(null)
    setError(null)
    setLoading(false)
  }

  return (
    <div className={styles.page}>

      <PageHero
        title="Correlation and Comparative Analysis"
        description="Run the grounded correlation workflow, including event studies, insider and price relationships, political and contract timing, and optional comparative output when competitors are supplied."
      />

      <div className={styles.layout}>
        <section className={styles.panel}>
          <h2 className={styles.panelTitle}>Request</h2>
          <form className={styles.form} onSubmit={onSubmit}>
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
                placeholder="EXM"
              />
            </label>

            <label className={styles.label}>
              Competitors
              <input
                className={styles.input}
                value={form.competitors}
                onChange={(event) => setForm((current) => ({ ...current, competitors: event.target.value }))}
                placeholder="CMP1, CMP2"
              />
              <span className={styles.helpText}>Optional comma-separated competitors for deep comparative analysis.</span>
            </label>

            <label className={styles.label}>
              Years
              <select
                className={styles.select}
                value={form.years}
                onChange={(event) => setForm((current) => ({ ...current, years: event.target.value }))}
              >
                {[1, 2, 3, 4, 5].map((years) => (
                  <option key={years} value={years}>{years}</option>
                ))}
              </select>
            </label>

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.button} disabled={loading}>
                {loading ? 'Running...' : 'Run Correlation Analysis'}
              </button>
              <button type="button" className={`${styles.button} ${styles.secondaryButton}`} onClick={onReset} disabled={loading}>
                Reset
              </button>
            </div>
          </form>
        </section>

        <div className={styles.results}>
          <ResultState result={result} error={error} loading={loading} />

          {result ? (
            <>
              <SectionCard title="Run Summary" aside={result.partial ? <span className={`${styles.pill} ${styles.pillMedium}`}>Partial</span> : <span className={`${styles.pill} ${styles.pillLow}`}>Complete</span>}>
                <KeyValueGrid
                  items={[
                    { label: 'Entity', value: result.entity_name || '-' },
                    { label: 'Ticker', value: result.ticker || '-' },
                    { label: 'CIK', value: result.cik || '-' },
                    { label: 'Correlation analyses run', value: formatNumber(correlations.ran) },
                    { label: 'Price bars', value: formatNumber(correlations.price_bars) },
                    { label: 'Comparative peers', value: formatNumber((deepComparative.peer_tickers || []).length || deepComparative.peer_count) },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Source Availability">
                <SourceStatusGrid sourceStatus={result.source_status} />
              </SectionCard>

              <SectionCard title="Insider and Price Relationships">
                <KeyValueGrid
                  items={[
                    { label: 'Observations', value: formatNumber(insiderTiming.n) },
                    { label: 'Correlation', value: insiderTiming.r !== undefined ? formatNumber(insiderTiming.r, 2) : '-' },
                    { label: 'Significant', value: insiderTiming.significant === undefined ? '-' : (insiderTiming.significant ? 'Yes' : 'No') },
                    { label: 'Confidence interval low', value: insiderTiming.ci_low !== undefined ? formatNumber(insiderTiming.ci_low, 2) : '-' },
                    { label: 'Confidence interval high', value: insiderTiming.ci_high !== undefined ? formatNumber(insiderTiming.ci_high, 2) : '-' },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Event Studies">
                <KeyValueGrid
                  items={[
                    { label: 'Events analyzed', value: formatNumber(eventReturns.n_events || eventReturns.n) },
                    { label: 'Mean abnormal return', value: eventReturns.mean_abnormal_return !== undefined ? formatPercent(eventReturns.mean_abnormal_return, 2) : '-' },
                    { label: 'Median abnormal return', value: eventReturns.median_abnormal_return !== undefined ? formatPercent(eventReturns.median_abnormal_return, 2) : '-' },
                    { label: 'Positive event rate', value: eventReturns.positive_rate !== undefined ? formatPercent(eventReturns.positive_rate, 1) : '-' },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Political and Contract Relationships">
                <KeyValueGrid
                  items={[
                    { label: 'Lobbying median lag (days)', value: formatNumber(lobbyingLag.median_lag_days) },
                    { label: 'Lobbying matches', value: formatNumber(lobbyingLag.matches) },
                    { label: 'Political contract overlap score', value: contractPolitical.overlap_score !== undefined ? formatNumber(contractPolitical.overlap_score, 2) : '-' },
                    { label: 'Political overlap events', value: formatNumber(contractPolitical.matches) },
                    { label: 'Contract value reviewed', value: contractPolitical.contract_value !== undefined ? formatCurrency(contractPolitical.contract_value) : '-' },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Deep Comparative Output">
                {Object.keys(deepComparative).length ? (
                  <>
                    <KeyValueGrid
                      items={[
                        { label: 'Target ticker', value: deepComparative.target_ticker || '-' },
                        { label: 'Peer count', value: formatNumber((deepComparative.peer_tickers || []).length || deepComparative.peer_count) },
                        { label: 'Best ranked peer', value: deepComparative.best_peer || '-' },
                        { label: 'Worst ranked peer', value: deepComparative.worst_peer || '-' },
                      ]}
                    />
                    {(deepComparative.rankings || []).length ? (
                      <SimpleTable
                        columns={[
                          { key: 'ticker', label: 'Ticker' },
                          { key: 'score', label: 'Score', numeric: true, render: (row) => formatNumber(row.score, 2) },
                          { key: 'summary', label: 'Summary' },
                        ]}
                        rows={deepComparative.rankings}
                      />
                    ) : null}
                  </>
                ) : (
                  <EmptyState>No comparative payload was returned. If competitors were omitted or data was unavailable, the source-status panel above should reflect that.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Warnings">
                <WarningList warnings={result.warnings || []} />
              </SectionCard>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
