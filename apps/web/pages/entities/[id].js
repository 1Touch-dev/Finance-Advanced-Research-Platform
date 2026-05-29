import { useRouter } from 'next/router'
import useSWR from 'swr'

const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:3001'
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
    <main style={{padding:20,fontFamily:'sans-serif'}}>
      <h1>Entity Profile</h1>
      <section>
        <h2>Overview</h2>
        <pre>{profile?JSON.stringify(profile,null,2):'Loading...'}</pre>
      </section>
      <section>
        <h2>Related Parties</h2>
        <pre>{related?JSON.stringify(related,null,2):'Loading...'}</pre>
      </section>
      <section>
        <h2>Relationships</h2>
        <pre>{rels?JSON.stringify(rels,null,2):'Loading...'}</pre>
      </section>
      <section>
        <h2>Evidence</h2>
        <pre>{refs?JSON.stringify(refs,null,2):'Loading...'}</pre>
      </section>
      <section>
        <h2>Timeline</h2>
        <pre>{timeline?JSON.stringify(timeline,null,2):'Loading...'}</pre>
      </section>
    </main>
  )
}
