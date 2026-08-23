import { useMemo, useState } from 'react'
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
  TagList,
  WarningList,
} from '../../src/components/intelligence/ActivationShared'
import {
  fetchNetworkAnalysis,
  formatIntelligenceError,
  splitCommaSeparated,
} from '../../lib/intelligence'

function ResultState({ result, error, loading }) {
  if (loading) {
    return <Notice tone="info" title="Running grounded network analysis">Checking founder overlaps, board interlocks, institutional holders, holder concentration, competitor overlap, and first-degree grounded relationships.</Notice>
  }
  if (error) {
    const parsed = formatIntelligenceError(error)
    return <Notice tone={parsed.status >= 500 || parsed.status === 0 ? 'error' : 'warn'} title={parsed.status ? `Request error (${parsed.status})` : 'Request error'}>{parsed.detail || parsed.message}</Notice>
  }
  if (!result) {
    return <Notice tone="info" title="Ready">Submit an entity to inspect only the grounded network data already available from the backend.</Notice>
  }
  if (!(result.founder_correlations?.nodes || []).length && !Object.keys(result.co_investment_network || {}).length) {
    return <Notice tone={result.partial ? 'warn' : 'success'} title={result.partial ? 'Partial network data returned' : 'No grounded network links found'}>{result.partial ? 'Some sources were unavailable for this run, so only partial grounded network output could be returned.' : 'The backend did not return grounded founder or co-investment links for these inputs.'}</Notice>
  }
  return <Notice tone="success" title="Grounded network data returned">This view shows only first-degree relationships and warnings explicitly returned by the backend.</Notice>
}

export default function IntelligenceNetworkPage() {
  const [form, setForm] = useState({
    entity_name: '',
    ticker: '',
    competitors: '',
    depth: 1,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const founderNodes = result?.founder_correlations?.nodes || []
  const founderEdges = result?.founder_correlations?.edges || []
  const boardPeople = result?.board_interlocks?.people || []
  const holderRows = result?.institutional_holders?.holders || []
  const competitorPeers = result?.institutional_overlap?.peers || []
  const overlapSummary = result?.institutional_overlap?.summary || {}
  const concentration = result?.position_concentration || {}
  const coordinated = result?.coordinated_movements || {}
  const founderStats = result?.founder_correlations?.network_stats || {}
  const founderFindings = result?.founder_correlations?.key_findings || []
  const coinvestStats = result?.co_investment_network?.network_stats || {}
  const coinvestFindings = result?.co_investment_network?.key_findings || []

  const boardRows = useMemo(() => (
    boardPeople.map((person, index) => ({
      id: `${person.name || 'person'}-${index}`,
      name: person.name || '-',
      issuerRoles: (person.roles_at_issuer || []).join(', '),
      otherSeats: (person.other_seats || []).map((seat) => seat.issuer).filter(Boolean).join(', '),
    }))
  ), [boardPeople])

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
      const response = await fetchNetworkAnalysis({
        entity_name: form.entity_name.trim(),
        ticker: form.ticker.trim().toUpperCase(),
        competitors: splitCommaSeparated(form.competitors),
        depth: Number(form.depth),
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
      depth: 1,
    })
    setResult(null)
    setError(null)
    setLoading(false)
  }

  return (
    <div className={styles.page}>

      <PageHero
        title="Intelligence Network Analysis"
        description="Review grounded founder overlap, board interlocks, holder clustering, concentration metrics, competitor overlap, and the backend's first-degree relationship warnings without implying unsupported second-degree links."
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
              <span className={styles.helpText}>Optional comma-separated peer tickers for overlap analysis.</span>
            </label>

            <label className={styles.label}>
              Requested Depth
              <select
                className={styles.select}
                value={form.depth}
                onChange={(event) => setForm((current) => ({ ...current, depth: event.target.value }))}
              >
                {[1, 2, 3, 4, 5].map((depth) => (
                  <option key={depth} value={depth}>{depth}</option>
                ))}
              </select>
              <span className={styles.helpText}>The backend currently limits output to grounded first-degree data and returns a warning when higher depth is requested.</span>
            </label>

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.button} disabled={loading}>
                {loading ? 'Running...' : 'Run Network Analysis'}
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
                    { label: 'Founder nodes', value: formatNumber(founderStats.node_count) },
                    { label: 'Founder edges', value: formatNumber(founderStats.edge_count) },
                    { label: 'Education connections', value: formatNumber(founderStats.education_connections) },
                    { label: 'Company connections', value: formatNumber(founderStats.company_connections) },
                    { label: 'Institutional holders', value: formatNumber(holderRows.length) },
                    { label: 'Herfindahl index', value: formatNumber(concentration.herfindahl_index, 2) },
                    { label: 'Largest holder share', value: concentration.largest_holder_pct !== undefined ? `${formatNumber(concentration.largest_holder_pct, 1)}%` : '-' },
                    { label: 'Avg overlap %', value: overlapSummary.avg_overlap_pct !== undefined ? `${formatNumber(overlapSummary.avg_overlap_pct, 1)}%` : '-' },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Source Availability">
                <SourceStatusGrid sourceStatus={result.source_status} />
              </SectionCard>

              <SectionCard title="Grounded First-Degree Relationships">
                {(founderNodes.length || founderEdges.length) ? (
                  <div className={styles.grid2}>
                    <div>
                      <h3 className={styles.panelTitle}>Nodes</h3>
                      <SimpleTable
                        columns={[
                          { key: 'label', label: 'Entity', render: (row) => row.label || row.name || row.id || '-' },
                          { key: 'kind', label: 'Kind', render: (row) => row.kind || row.type || '-' },
                        ]}
                        rows={founderNodes}
                      />
                    </div>
                    <div>
                      <h3 className={styles.panelTitle}>Edges</h3>
                      <SimpleTable
                        columns={[
                          { key: 'source', label: 'Source', render: (row) => row.source || row.src || '-' },
                          { key: 'target', label: 'Target', render: (row) => row.target || row.dst || '-' },
                          { key: 'label', label: 'Relationship', render: (row) => row.label || row.kind || '-' },
                        ]}
                        rows={founderEdges}
                      />
                    </div>
                  </div>
                ) : (
                  <EmptyState>No grounded founder relationship graph data was returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Founder and Executive Overlaps">
                {founderFindings.length ? <TagList values={founderFindings} /> : <EmptyState>No grounded founder overlap findings were returned.</EmptyState>}
              </SectionCard>

              <SectionCard title="Board Interlocks">
                {boardRows.length ? (
                  <SimpleTable
                    columns={[
                      { key: 'name', label: 'Person' },
                      { key: 'issuerRoles', label: 'Roles at issuer' },
                      { key: 'otherSeats', label: 'Other seats' },
                    ]}
                    rows={boardRows}
                  />
                ) : (
                  <EmptyState>No board interlocks were returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Institutional Holder Clustering">
                {holderRows.length ? (
                  <SimpleTable
                    columns={[
                      { key: 'institution', label: 'Holder', render: (row) => row.institution || row.manager || row.name || '-' },
                      { key: 'shares', label: 'Shares', numeric: true, render: (row) => formatNumber(row.shares) },
                      { key: 'value', label: 'Value', numeric: true, render: (row) => formatCurrency(row.value) },
                      { key: 'pct', label: 'Pct', numeric: true, render: (row) => row.pct !== undefined ? `${formatNumber(row.pct, 2)}%` : '-' },
                    ]}
                    rows={holderRows}
                  />
                ) : (
                  <EmptyState>No institutional holder cluster rows were returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Co-Investment Network">
                {Object.keys(result.co_investment_network || {}).length ? (
                  <div className={styles.grid2}>
                    <KeyValueGrid
                      items={[
                        { label: 'Nodes', value: formatNumber(coinvestStats.node_count) },
                        { label: 'Edges', value: formatNumber(coinvestStats.edge_count) },
                        { label: 'Shared holders', value: formatNumber(coinvestStats.shared_holder_count) },
                        { label: 'Top shared holders', value: formatNumber(coinvestStats.top_shared_holder_count) },
                      ]}
                    />
                    <div>
                      <h3 className={styles.panelTitle}>Key Findings</h3>
                      {coinvestFindings.length ? <TagList values={coinvestFindings} /> : <EmptyState>No co-investment key findings were returned.</EmptyState>}
                    </div>
                  </div>
                ) : (
                  <EmptyState>No grounded co-investment network was returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Concentration Metrics">
                <KeyValueGrid
                  items={[
                    { label: 'Herfindahl index', value: formatNumber(concentration.herfindahl_index, 2) },
                    { label: 'Largest holder %', value: concentration.largest_holder_pct !== undefined ? `${formatNumber(concentration.largest_holder_pct, 1)}%` : '-' },
                    { label: 'Total holder value', value: formatCurrency(concentration.total_value) },
                    { label: 'Total holder shares', value: formatNumber(concentration.total_shares) },
                  ]}
                />
              </SectionCard>

              <SectionCard title="Competitor Overlaps">
                {competitorPeers.length ? (
                  <SimpleTable
                    columns={[
                      { key: 'ticker', label: 'Peer' },
                      { key: 'overlap_pct', label: 'Overlap %', numeric: true, render: (row) => row.overlap_pct !== undefined ? `${formatNumber(row.overlap_pct, 2)}%` : '-' },
                      { key: 'shared_holders', label: 'Shared holders', numeric: true, render: (row) => formatNumber(row.shared_holders) },
                    ]}
                    rows={competitorPeers}
                  />
                ) : Object.keys(overlapSummary).length ? (
                  <KeyValueGrid
                    items={Object.entries(overlapSummary).map(([key, value]) => ({
                      label: key.replace(/_/g, ' '),
                      value: typeof value === 'number' ? formatNumber(value, 2) : String(value),
                    }))}
                  />
                ) : (
                  <EmptyState>No competitor overlap data was returned.</EmptyState>
                )}
              </SectionCard>

              <SectionCard title="Coordinated Movements">
                {(coordinated.position_changes || []).length ? (
                  <SimpleTable
                    columns={[
                      { key: 'institution', label: 'Holder' },
                      { key: 'direction', label: 'Direction' },
                      { key: 'change_pct', label: 'Change %', numeric: true, render: (row) => row.change_pct !== undefined ? `${formatNumber(row.change_pct, 2)}%` : '-' },
                    ]}
                    rows={coordinated.position_changes}
                  />
                ) : (
                  <EmptyState>No coordinated movements were returned. If historical holder series are unavailable, the warning list should explain that state.</EmptyState>
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
