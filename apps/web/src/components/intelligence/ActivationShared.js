import Link from 'next/link'
import { useMemo } from 'react'
import styles from '../../styles/IntelligenceActivation.module.css'

function titleCase(value) {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase())
}

export function formatCurrency(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return String(value)
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: number >= 100 ? 0 : 2,
  }).format(number)
}

export function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return String(value)
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
  }).format(number)
}

export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return String(value)
  }
  const normalized = Math.abs(number) <= 1 ? number * 100 : number
  return `${normalized.toFixed(digits)}%`
}

export function pillTone(value) {
  const text = String(value || '').toLowerCase()
  if (['high', 'error', 'unavailable', 'failed', 'elevated'].includes(text)) {
    return styles.pillHigh
  }
  if (['medium', 'partial', 'warning', 'missing_input'].includes(text)) {
    return styles.pillMedium
  }
  if (['low', 'clear', 'ok', 'success', 'supported', 'complete', 'documented'].includes(text)) {
    return styles.pillLow
  }
  return ''
}

export function PageHero({ title, description, eyebrow = 'Intelligence Activation' }) {
  return (
    <section className={styles.hero}>
      <p className={styles.eyebrow}>{eyebrow}</p>
      <h1 className={styles.heroTitle}>{title}</h1>
      <p className={styles.heroCopy}>{description}</p>
    </section>
  )
}

export function SectionCard({ title, children, aside }) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        {aside || null}
      </div>
      {children}
    </section>
  )
}

export function Notice({ tone = 'info', title, children }) {
  const toneClass = tone === 'success'
    ? styles.noticeSuccess
    : tone === 'warn'
      ? styles.noticeWarn
      : tone === 'error'
        ? styles.noticeError
        : styles.noticeInfo

  return (
    <div className={`${styles.notice} ${toneClass}`}>
      {title ? <p className={styles.noticeTitle}>{title}</p> : null}
      {children ? <div className={styles.noticeCopy}>{children}</div> : null}
    </div>
  )
}

export function KeyValueGrid({ items = [] }) {
  const filtered = items.filter((item) => item && item.label)
  if (!filtered.length) {
    return <p className={styles.empty}>No structured fields returned.</p>
  }
  return (
    <div className={styles.metaGrid}>
      {filtered.map((item) => (
        <div key={item.label} className={styles.metaCard}>
          <span className={styles.metaLabel}>{item.label}</span>
          <div className={styles.metaValue}>{item.value ?? '-'}</div>
        </div>
      ))}
    </div>
  )
}

export function TagList({ values = [] }) {
  if (!values.length) {
    return <p className={styles.empty}>None returned.</p>
  }
  return (
    <div className={styles.tags}>
      {values.map((value, index) => (
        <span key={`${value}-${index}`} className={styles.tag}>{String(value)}</span>
      ))}
    </div>
  )
}

export function WarningList({ warnings = [] }) {
  if (!warnings.length) {
    return <p className={styles.empty}>No warnings returned.</p>
  }
  return (
    <ul className={styles.plainList}>
      {warnings.map((warning, index) => (
        <li key={`${warning.code || warning.detail || index}-${index}`} className={`${styles.plainListItem} ${styles.warningItem}`}>
          <div className={styles.inlineGroup}>
            {warning.source ? <span className={`${styles.pill} ${pillTone(warning.source)}`}>{warning.source}</span> : null}
            {warning.code ? <span className={styles.pill}>{warning.code}</span> : null}
          </div>
          <p className={styles.noticeCopy}>{warning.detail || 'Warning returned by backend.'}</p>
        </li>
      ))}
    </ul>
  )
}

export function SourceStatusGrid({ sourceStatus = {} }) {
  const entries = Object.entries(sourceStatus || {})
  if (!entries.length) {
    return <p className={styles.empty}>No source-status details returned.</p>
  }
  return (
    <div className={styles.sourceGrid}>
      {entries.map(([name, status]) => (
        <div key={name} className={styles.sourceCard}>
          <div className={styles.sourceHeader}>
            <span className={styles.sourceName}>{titleCase(name)}</span>
            <span className={`${styles.pill} ${pillTone(status?.status)}`}>{status?.status || 'unknown'}</span>
          </div>
          <p className={styles.sourceDetail}>
            {status?.detail || (status?.used ? 'Used in this run.' : 'No additional detail returned.')}
          </p>
        </div>
      ))}
    </div>
  )
}

export function JsonBlock({ value }) {
  const pretty = useMemo(() => JSON.stringify(value, null, 2), [value])
  return <pre className={styles.codeBlock}>{pretty}</pre>
}

export function SimpleTable({ columns = [], rows = [] }) {
  if (!rows.length) {
    return <p className={styles.empty}>No rows returned.</p>
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={column.numeric ? styles.numeric : ''}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={row.id || row.key || rowIndex}>
              {columns.map((column) => (
                <td key={column.key} className={column.numeric ? styles.numeric : ''}>
                  {column.render ? column.render(row, rowIndex) : (row[column.key] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function PageActions({ children }) {
  return <div className={styles.inlineGroup}>{children}</div>
}

export function IframeReport({ html }) {
  return (
    <div className={styles.iframeWrap}>
      <iframe
        title="Interactive intelligence report"
        className={styles.iframe}
        sandbox="allow-scripts"
        srcDoc={html || '<html><body></body></html>'}
      />
    </div>
  )
}

export function ReportLinkButton({ href, children }) {
  return (
    <Link href={href} className={styles.linkButton}>
      {children}
    </Link>
  )
}

export function EmptyState({ children }) {
  return <p className={styles.empty}>{children}</p>
}
