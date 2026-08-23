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
  WarningList,
} from '../../src/components/intelligence/ActivationShared'
import {
  fetchContractProbabilityAnalysis,
  formatIntelligenceError,
  splitCommaSeparated,
} from '../../lib/intelligence'

function ResultState({ result, error, loading }) {
  if (loading) {
    return <Notice tone="info" title="Calculating grounded contract probability">Checking historical awards, recompetes, open opportunities, concentration risk, and evidence-backed warnings.</Notice>
  }
  if (error) {
    const parsed = formatIntelligenceError(error)
    return <Notice tone={parsed.status >= 500 || parsed.status === 0 ? 'error' : 'warn'} title={parsed.status ? `Request error (${parsed.status})` : 'Request error'}>{parsed.detail || parsed.message}</Notice>
  }
  if (!result) {
    return <Notice tone="info" title="Ready">Submit an entity to inspect the current grounded contract-probability output from the backend.</Notice>
  }

  const weightedProbability = result.analysis?.opportunity_pipeline?.weighted_avg_win_probability
  if (weightedProbability === null) {
    return <Notice tone="warn" title="Insufficient evidence for a grounded win probability">The backend intentionally withheld a percentage because historical awards or open opportunities were unavailable or insufficient.</Notice>
  }
  return <Notice tone="success" title="Contract probability output returned">Review the probability, evidence, opportunity pipeline, and warnings before using the result operationally.</Notice>
}

export default function ContractProbabilityPage() {
  const [form, setForm] = useState({
    entity_name: '',
    ticker: '',
    naics_codes: '',
    keywords: '',
    total_revenue: '',
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const analysis = result?.analysis || {}
  const history = analysis.historical_performance || {}
  const concentration = analysis.concentration_risk || {}
  const recompete = analysis.recompete_pipeline || {}
  const pipeline = analysis.opportunity_pipeline || {}
  const keyInsights = analysis.key_insights || []

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
      const totalRevenue = form.total_revenue.trim() === '' ? null : Number(form.total_revenue)
      const response = await fetchContractProbabilityAnalysis({
        entity_name: form.entity_name.trim(),
        ticker: form.ticker.trim().toUpperCase(),
        naics_codes: splitCommaSeparated(form.naics_codes),
        keywords: splitCommaSeparated(form.keywords),
        total_revenue: Number.isFinite(totalRevenue) ? totalRevenue : null,
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
      naics_codes: '',
      keywords: '',
      total_revenue: '',
    })
    setResult(null)
    setError(null)
    setLoading(false)
  }

  return (
    <div className={styles.page}>

      <PageHero
        title="Contract Probability"
        description="Review the grounded government-contract probability workflow, including historical performance, concentration risk, recompete exposure, top opportunities, evidence-backed warnings, and honest unavailable states."
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
              NAICS Codes
              <input
                className={styles.input}
                value={form.naics_codes}
                onChange={(event) => setForm((current) => ({ ...current, naics_codes: event.target.value }))}
                placeholder="541511, 541512"
              />
              <span className={styles.helpText}>Optional comma-separated NAICS codes passed directly to the backend.</span>
            </label>

            <label className={styles.label}>
              Keywords
              <input
                className={styles.input}
                value={form.keywords}
                onChange={(event) => setForm((current) => ({ ...current, keywords: event.target.value }))}
                placeholder="cloud, cyber, analytics"
              />
              <span className={styles.helpText}>Optional comma-separated opportunity keywords.</span>
            </label>

            <label className={styles.label}>
              Total Revenue
              <input
                className={styles.input}
                type="number"
                min="0"
                step="0.01"
                value={form.total_revenue}
                onChange={(event) => setForm((current) => ({ ...current, total_revenue: event.target.value }))}
                placeholder="1000000000"
              />
            </label>

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.button} disabled={loading}>
                {loading ? 'Running...' : 'Run Contract Probability'}
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
              <SectionCard title="Probability Summary" aside={pipeline.weighted_avg_win_probability === null ? <span className={`${styles.pill} ${styles.pillMedium}`}>Unavailable</span> : <span className={`${styles.pill} ${styles.pillLow}`}>Available</span>}>
                <KeyValueGrid
                  items={[
                    { label: 'Entity', value: result.entity_name || analysis.company || '-' },
                    { label: 'Ticker', value: result.ticker || analysis.ticker || '-' },
                    { label: 'Analysis date', value: analysis.analysis_date || '-' },
                    { label: 'Weighted avg win probability', value: pipeline.weighted_avg_win_probability === null ? 'Not returned' : formatPercent(pipeline.weighted_avg_win_probability, 0) },
                    { label: 'Opportunities identified', value: formatNumber(pipeline.opportunities_identified) },
                    { label: 'Total estimated value', value: formatCurrency(pipeline.total_estimated_value) },
                    { label: 'Contracts at high recompete risk', value: formatNumber(recompete.high_risk_count) },
                    { label: 'Value at risk', value: formatCurrency(recompete.value_at_risk) },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Historical Performance">
                <KeyValueGrid
                  items={[
                    { label: 'Awards (5 years)', value: formatNumber(history.total_awards_5yr) },
                    { label: 'Value (5 years)', value: formatCurrency(history.total_value_5yr) },
                    { label: 'Average award size', value: formatCurrency(history.avg_award_size) },
                    { label: 'Agencies served', value: (history.agencies_served || []).join(', ') || '-' },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Concentration Risk">
                <KeyValueGrid
                  items={[
                    { label: 'Risk level', value: concentration.concentration_risk || 'Unknown' },
                    { label: 'Total contract value', value: formatCurrency(concentration.total_contract_value) },
                    { label: 'Top agency concentration', value: formatPercent(concentration.top_agency_concentration, 1) },
                    { label: 'Top contract concentration', value: formatPercent(concentration.top_contract_concentration, 1) },
                    { label: 'Government revenue %', value: concentration.government_revenue_pct === null || concentration.government_revenue_pct === undefined ? '-' : formatPercent(concentration.government_revenue_pct, 1) },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Recompete Pipeline">
                {(recompete.upcoming_recompetes || []).length ? (
                  <SimpleTable
                    columns={[
                      { key: 'agency', label: 'Agency' },
                      { key: 'amount', label: 'Amount', numeric: true, render: (row) => formatCurrency(row.amount) },
                      { key: 'months_until_recompete', label: 'Months', numeric: true, render: (row) => formatNumber(row.months_until_recompete, 1) },
                      { key: 'recompete_risk', label: 'Risk' },
                    ]}
                    rows={recompete.upcoming_recompetes}
                  />
                ) : (
                  <EmptyState>No upcoming recompetes were returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Opportunity Pipeline">
                {(pipeline.top_opportunities || []).length ? (
                  <SimpleTable
                    columns={[
                      { key: 'title', label: 'Opportunity' },
                      { key: 'agency', label: 'Agency' },
                      { key: 'naics', label: 'NAICS' },
                      { key: 'win_probability', label: 'Probability', numeric: true, render: (row) => {
                        const probability = row.win_probability?.probability
                        return probability === undefined || probability === null ? '-' : formatPercent(probability, 0)
                      } },
                    ]}
                    rows={pipeline.top_opportunities}
                  />
                ) : (
                  <EmptyState>No open opportunity rows were returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Supporting Evidence">
                {keyInsights.length ? (
                  <ul className={styles.list}>
                    {keyInsights.map((insight, index) => <li key={`${insight}-${index}`}>{insight}</li>)}
                  </ul>
                ) : (
                  <EmptyState>No narrative evidence was returned.</EmptyState>
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
