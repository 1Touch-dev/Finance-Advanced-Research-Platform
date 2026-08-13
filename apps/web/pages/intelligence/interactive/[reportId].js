import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/router'
import styles from '../../../src/styles/IntelligenceActivation.module.css'
import {
  IframeReport,
  Notice,
  PageHero,
  PageActions,
  ReportLinkButton,
} from '../../../src/components/intelligence/ActivationShared'
import {
  fetchInteractiveReport,
  formatIntelligenceError,
} from '../../../lib/intelligence'

export default function InteractiveReportByIdPage() {
  const router = useRouter()
  const { reportId } = router.query
  const [html, setHtml] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const requestRef = useRef(0)

  useEffect(() => {
    if (!router.isReady || !reportId) {
      return
    }

    const requestId = requestRef.current + 1
    requestRef.current = requestId
    setLoading(true)
    setError(null)
    setHtml('')

    fetchInteractiveReport(reportId)
      .then((response) => {
        if (requestRef.current !== requestId) {
          return
        }
        setHtml(response.html || '')
      })
      .catch((requestError) => {
        if (requestRef.current !== requestId) {
          return
        }
        setError(requestError)
      })
      .finally(() => {
        if (requestRef.current === requestId) {
          setLoading(false)
        }
      })

    return () => {
      requestRef.current += 1
    }
  }, [router.isReady, reportId])

  const parsedError = error ? formatIntelligenceError(error) : null

  return (
    <div className={styles.page}>
      <PageHero
        title="Interactive Report Viewer"
        description="Open the persisted interactive HTML for a saved intelligence report. Historical reports that predate interactive payload support are handled as a clear compatibility message rather than a generic crash."
      />

      {loading ? (
        <Notice tone="info" title="Loading interactive report">Fetching report {reportId} from the backend interactive route.</Notice>
      ) : null}

      {parsedError ? (
        <Notice tone={parsedError.status === 409 ? 'warn' : parsedError.status >= 500 || parsedError.status === 0 ? 'error' : 'warn'} title={parsedError.status === 409 ? 'Historical report is not interactive' : parsedError.status ? `Request error (${parsedError.status})` : 'Request error'}>
          {parsedError.detail || parsedError.message}
        </Notice>
      ) : null}

      {!loading && !parsedError && !html ? (
        <Notice tone="info" title="Ready">The interactive HTML will render here once the route resolves.</Notice>
      ) : null}

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Saved report actions</h2>
        </div>
        <PageActions>
          <ReportLinkButton href="/saved">Saved reports</ReportLinkButton>
          {reportId ? <ReportLinkButton href={`/intelligence/${reportId}`}>Base report</ReportLinkButton> : null}
        </PageActions>
      </section>

      {html ? <IframeReport html={html} /> : null}
    </div>
  )
}
