import { useRouter } from 'next/router'
import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { getApiBaseUrl } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'
import eStyles from '../../src/styles/Entity.module.css'

const API = getApiBaseUrl()
const fetcher = (url) => fetch(url).then(r => r.json())

// ── Small components ──────────────────────────────────────────────────────────

function Badge({ label, color = '#818cf8' }) {
  return (
    <span style={{
      background: `${color}22`,
      border: `1px solid ${color}55`,
      borderRadius: 6,
      color,
      fontSize: '0.72rem',
      fontWeight: 700,
      letterSpacing: '0.06em',
      padding: '0.15rem 0.5rem',
      textTransform: 'uppercase',
    }}>{label}</span>
  )
}

function Stat({ label, value, sub }) {
  return (
    <div className={eStyles.stat}>
      <span className={eStyles.statVal}>{value ?? '—'}</span>
      <span className={eStyles.statLabel}>{label}</span>
      {sub && <span className={eStyles.statSub}>{sub}</span>}
    </div>
  )
}

function RelCard({ rel, entityId, onInvestigate }) {
  const isSource = rel.source_entity_id === Number(entityId)
  const partner  = isSource ? rel.target_entity_name : rel.source_entity_name
  const arrow    = isSource ? '→' : '←'
  const colors   = {
    employs:          '#60a5fa',
    investor:         '#a78bfa',
    lobbying:         '#f97316',
    lobbying_client:  '#fb923c',
    lobbying_registrant: '#fb923c',
    fara_registrant:  '#fb7185',
    contract:         '#4ade80',
    board_member:     '#818cf8',
  }
  const color = colors[rel.kind] || '#94a3b8'
  return (
    <div className={eStyles.relCard}>
      <span style={{ color, fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase' }}>
        {rel.kind?.replace(/_/g, ' ')}
      </span>
      <span className={eStyles.relArrow}>{arrow}</span>
      <span
        className={eStyles.relName}
        onClick={() => partner && onInvestigate(partner)}
        title="Click to investigate"
      >{partner || '—'}</span>
    </div>
  )
}

function EvidenceRow({ ev }) {
  return (
    <div className={eStyles.evRow}>
      <span className={eStyles.evSource}>{ev.source_name || ev.source_id}</span>
      <span className={eStyles.evText}>{(ev.content || ev.text || '')?.slice(0, 200)}</span>
      {ev.url && (
        <a href={ev.url} target="_blank" rel="noopener noreferrer" className={eStyles.evLink}>↗</a>
      )}
    </div>
  )
}

function TimelineItem({ item }) {
  const colorMap = { legal: '#f87171', financial: '#60a5fa', government: '#4ade80', news: '#fbbf24' }
  const color = colorMap[item.category?.toLowerCase()] || '#818cf8'
  return (
    <div className={eStyles.tlItem}>
      <div className={eStyles.tlDot} style={{ background: color }} />
      <div className={eStyles.tlContent}>
        <span className={eStyles.tlDate}>{item.date || item.year || '—'}</span>
        <span className={eStyles.tlText}>{item.text || item.description || ''}</span>
        {item.source && <span className={eStyles.tlSource}>{item.source}</span>}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function EntityProfile() {
  const router   = useRouter()
  const { id }   = router.query
  const [tab, setTab] = useState('overview')

  const { data: profile,  error: profErr  } = useSWR(id ? `${API}/search/entities/${id}` : null, fetcher)
  const { data: rels,     error: relsErr   } = useSWR(id ? `${API}/search/entities/${id}/relationships` : null, fetcher)
  const { data: evidence, error: evErr     } = useSWR(id ? `${API}/search/entities/${id}/evidence` : null, fetcher)
  const { data: timeline, error: tlErr     } = useSWR(id ? `${API}/search/entities/${id}/timeline` : null, fetcher)
  const { data: related,  error: relErr    } = useSWR(id ? `${API}/graph/related?entity_id=${id}` : null, fetcher)

  const entity    = profile?.entity || profile || {}
  const relList   = (rels?.relationships || rels || []).slice(0, 50)
  const evList    = (evidence?.evidence  || evidence || []).slice(0, 30)
  const tlList    = (timeline?.timeline  || timeline || []).slice(0, 40)
  const relatedList = (related?.entities || related?.nodes || []).slice(0, 20)

  const entityKind = entity.entity_type || entity.kind || 'entity'
  const entityName = entity.name || entity.entity_name || `Entity #${id}`

  const investigate = (name) => {
    router.push(`/intelligence?entity=${encodeURIComponent(name)}`)
  }

  const tabs = ['overview', 'relationships', 'evidence', 'timeline', 'related']

  if (!id) {
    return (
      <main className={styles.page}>
        <section className={styles.hero}>
          <h1>Entity Profile</h1>
          <p>No entity ID specified. Go to <Link href="/search">Search</Link> to find an entity.</p>
        </section>
      </main>
    )
  }

  return (
    <main className={styles.page}>
      {/* Header */}
      <section className={styles.hero}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
          <div className={eStyles.avatar}>
            {entityName.charAt(0).toUpperCase()}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
              <Badge label={entityKind} color="#818cf8" />
              {entity.is_us && <Badge label="US Entity" color="#4ade80" />}
              {entity.sanctions_flag && <Badge label="Sanctions Risk" color="#f87171" />}
              {entity.public_company && <Badge label="Public" color="#60a5fa" />}
            </div>
            <h1 style={{ margin: 0 }}>{entityName}</h1>
            {entity.description && (
              <p style={{ margin: '0.4rem 0 0', color: 'var(--text-muted)', maxWidth: 640 }}>
                {entity.description?.slice(0, 300)}
              </p>
            )}
            {entity.sec_cik && (
              <a
                href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${entity.sec_cik}&type=&dateb=&owner=include&count=40`}
                target="_blank" rel="noopener noreferrer"
                style={{ fontSize: '0.78rem', color: '#818cf8', marginTop: '0.3rem', display: 'inline-block' }}
              >SEC EDGAR ↗</a>
            )}
            <div style={{ marginTop: '0.6rem', display: 'flex', gap: '0.5rem' }}>
              <button
                className={eStyles.investigateBtn}
                onClick={() => investigate(entityName)}
              >🔍 Generate Intelligence Report</button>
              <Link href={`/graph?entity_id=${id}`} passHref>
                <a className={eStyles.graphBtn}>🕸 View Relationship Graph</a>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* KPI bar */}
      <div className={eStyles.statBar}>
        <Stat label="Relationships" value={relList.length} sub="mapped" />
        <Stat label="Evidence Items" value={evList.length} sub="cited" />
        <Stat label="Timeline Events" value={tlList.length} sub="chronological" />
        <Stat label="Related Parties" value={relatedList.length} sub="in graph" />
        {entity.total_obligated_usd > 0 && (
          <Stat label="Gov't Contracts" value={`$${(entity.total_obligated_usd/1e6).toFixed(1)}M`} sub="obligated" />
        )}
        {entity.sec_cik && <Stat label="SEC CIK" value={entity.sec_cik} sub="EDGAR" />}
      </div>

      {/* Tabs */}
      <div className={eStyles.tabs}>
        {tabs.map(t => (
          <button
            key={t}
            className={`${eStyles.tab} ${tab === t ? eStyles.tabActive : ''}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className={styles.panel}>
          <h2>Entity Details</h2>
          <div className={eStyles.detailGrid}>
            {Object.entries(entity).filter(([k]) => !['id','created_at','updated_at','description'].includes(k)).map(([k, v]) => (
              <div key={k} className={eStyles.detailRow}>
                <span className={eStyles.detailKey}>{k.replace(/_/g, ' ')}</span>
                <span className={eStyles.detailVal}>
                  {typeof v === 'object' ? JSON.stringify(v).slice(0, 120) : String(v ?? '—')}
                </span>
              </div>
            ))}
          </div>
          {relatedList.length > 0 && (
            <>
              <h3 style={{ marginTop: '1.5rem' }}>Top Related Parties</h3>
              <div className={eStyles.relGrid}>
                {relatedList.slice(0, 8).map((r, i) => (
                  <div key={i} className={eStyles.relChip}
                       onClick={() => investigate(r.name || r.entity_name || '')}>
                    {r.name || r.entity_name || `#${r.id}`}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'relationships' && (
        <div className={styles.panel}>
          <h2>Relationships <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 400 }}>({relList.length})</span></h2>
          {relList.length === 0 && <p className={styles.empty}>No relationships mapped yet.</p>}
          <div className={eStyles.relList}>
            {relList.map((r, i) => <RelCard key={i} rel={r} entityId={id} onInvestigate={investigate} />)}
          </div>
        </div>
      )}

      {tab === 'evidence' && (
        <div className={styles.panel}>
          <h2>Evidence & Citations <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 400 }}>({evList.length})</span></h2>
          {evList.length === 0 && <p className={styles.empty}>No evidence items found.</p>}
          <div className={eStyles.evList}>
            {evList.map((ev, i) => <EvidenceRow key={i} ev={ev} />)}
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <div className={styles.panel}>
          <h2>Event Timeline <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 400 }}>({tlList.length})</span></h2>
          {tlList.length === 0 && <p className={styles.empty}>No timeline events found for this entity.</p>}
          <div className={eStyles.timeline}>
            {tlList.map((item, i) => <TimelineItem key={i} item={item} />)}
          </div>
        </div>
      )}

      {tab === 'related' && (
        <div className={styles.panel}>
          <h2>Related Parties <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 400 }}>({relatedList.length})</span></h2>
          {relatedList.length === 0 && <p className={styles.empty}>No related parties found.</p>}
          <div className={eStyles.relGrid}>
            {relatedList.map((r, i) => (
              <div key={i} className={eStyles.relChipLarge}
                   onClick={() => investigate(r.name || r.entity_name || '')}>
                <span className={eStyles.relChipName}>{r.name || r.entity_name || `#${r.id}`}</span>
                {r.entity_type && <span className={eStyles.relChipType}>{r.entity_type}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  )
}
