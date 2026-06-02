import { useRouter } from 'next/router'
import useSWR from 'swr'
import { getApiBaseUrl } from '../../lib/api'
import styles from '../../src/styles/Page.module.css'

const API=getApiBaseUrl()
const fetcher=(url)=>fetch(url).then(r=>r.json())

export default function EntityProfile(){
  const router=useRouter();
  const {id}=router.query;
  const {data:profile}=useSWR(id?`${API}/search/entities/${id}`:null, fetcher)
  const {data:rels}=useSWR(id?`${API}/search/entities/${id}/relationships`:null, fetcher)
  const {data:refs}=useSWR(id?`${API}/search/entities/${id}/evidence`:null, fetcher)
  const {data:timeline}=useSWR(id?`${API}/search/entities/${id}/timeline`:null, fetcher)
  const {data:related}=useSWR(id?`${API}/graph/related?entity_id=${id}`:null, fetcher)
  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <h1>Entity Profile</h1>
        <p>Unified identity, relationship, evidence, and timeline view for entity ID `{id ?? '...'}`.</p>
      </section>
      <section className={styles.panel}>
        <h2>Overview</h2>
        <pre className={styles.mono}>{profile?JSON.stringify(profile,null,2):'Loading...'}</pre>
      </section>
      <section className={styles.panel}>
        <h2>Related Parties</h2>
        <pre className={styles.mono}>{related?JSON.stringify(related,null,2):'Loading...'}</pre>
      </section>
      <section className={styles.panel}>
        <h2>Relationships</h2>
        <pre className={styles.mono}>{rels?JSON.stringify(rels,null,2):'Loading...'}</pre>
      </section>
      <section className={styles.panel}>
        <h2>Evidence</h2>
        <pre className={styles.mono}>{refs?JSON.stringify(refs,null,2):'Loading...'}</pre>
      </section>
      <section className={styles.panel}>
        <h2>Timeline</h2>
        <pre className={styles.mono}>{timeline?JSON.stringify(timeline,null,2):'Loading...'}</pre>
      </section>
    </main>
  )
}
