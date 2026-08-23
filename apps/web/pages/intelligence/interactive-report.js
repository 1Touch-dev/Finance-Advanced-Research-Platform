import { useRef, useState } from 'react'
import styles from '../../src/styles/IntelligenceActivation.module.css'
import {
  IframeReport,
  Notice,
  PageHero,
  PageActions,
  ReportLinkButton,
} from '../../src/components/intelligence/ActivationShared'
import {
  createInteractiveReport,
  formatIntelligenceError,
} from '../../lib/intelligence'

export default function InteractiveReportPage() {
  const [form, setForm] = useState({
    entity_name: '',
    entity_type: 'org',
    ticker: '',
  })
  const [html, setHtml] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const currentRequest = useRef(0)

  const onSubmit = async (event) => {
    event.preventDefault()
    if (loading) {
      return
    }
    if (!form.entity_name.trim()) {
      setError({ status: 400, message: 'Entity name is required.', detail: 'entity_name: field required', raw: null })
      setHtml('')
      return
    }

    const requestId = currentRequest.current + 1
    currentRequest.current = requestId

    setLoading(true)
    setError(null)
    setHtml('')

    try {
      const response = await createInteractiveReport({
        entity_name: form.entity_name.trim(),
        entity_type: form.entity_type,
        ticker: form.ticker.trim().toUpperCase(),
      })
      if (currentRequest.current !== requestId) {
        return
      }
      setHtml(response.html || '')
    } catch (requestError) {
      if (currentRequest.current !== requestId) {
        return
      }
      setError(requestError)
    } finally {
      if (currentRequest.current === requestId) {
        setLoading(false)
      }
    }
  }

  const onReset = () => {
    currentRequest.current += 1
    setForm({
      entity_name: '',
      entity_type: 'org',
      ticker: '',
    })
    setHtml('')
    setError(null)
    setLoading(false)
  }

  const parsedError = error ? formatIntelligenceError(error) : null

  return (
    <div className={styles.page}>

      <PageHero
        title="Interactive Report"
        description="Generate a fresh interactive intelligence report directly from the backend HTML endpoint. This is for newly generated compatible content; historical reports can be opened from their saved report pages."
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
              Entity Type
              <select
                className={styles.select}
                value={form.entity_type}
                onChange={(event) => setForm((current) => ({ ...current, entity_type: event.target.value }))}
              >
                <option value="org">org</option>
                <option value="person">person</option>
              </select>
            </label>

            <label className={styles.label}>
              Ticker
              <input
                className={styles.input}
                value={form.ticker}
                onChange={(event) => setForm((current) => ({ ...current, ticker: event.target.value.toUpperCase() }))}
                placeholder="Optional"
              />
            </label>

            <div className={styles.buttonRow}>
              <button type="submit" className={styles.button} disabled={loading}>
                {loading ? 'Generating...' : 'Open Interactive Report'}
              </button>
              <button type="button" className={`${styles.button} ${styles.secondaryButton}`} onClick={onReset} disabled={loading}>
                Reset
              </button>
            </div>
          </form>
        </section>

        <div className={styles.results}>
          {loading ? (
            <Notice tone="info" title="Generating interactive report">Waiting for the backend to return compatible HTML.</Notice>
          ) : null}

          {parsedError ? (
            <Notice tone={parsedError.status >= 500 || parsedError.status === 0 ? 'error' : 'warn'} title={parsedError.status ? `Request error (${parsedError.status})` : 'Request error'}>
              {parsedError.detail || parsedError.message}
            </Notice>
          ) : null}

          {!loading && !parsedError && !html ? (
            <Notice tone="info" title="Ready">Submit a request to render the backend HTML in a controlled iframe. For saved reports, use the dedicated report viewer route instead.</Notice>
          ) : null}

          {html ? (
            <>
              <section className={styles.section}>
                <div className={styles.sectionHeader}>
                  <h2 className={styles.sectionTitle}>Interactive HTML</h2>
                </div>
                <PageActions>
                  <ReportLinkButton href="/saved">Open saved reports</ReportLinkButton>
                </PageActions>
              </section>
              <IframeReport html={html} />
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
