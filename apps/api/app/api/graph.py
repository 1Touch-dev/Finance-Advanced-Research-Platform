from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Set
from datetime import datetime, timezone
from app.db.session import get_db

router = APIRouter(prefix="/graph")


def fetch_neighbors(db: Session, node_ids: List[int], limit: int = 100) -> Dict[str, Any]:
    if not node_ids:
        return {"nodes": [], "edges": []}
    q = text("""
        select r.id, r.src_entity_id, r.dst_entity_id, r.kind
        from relationships r
        where r.src_entity_id = any(:ids) or r.dst_entity_id = any(:ids)
        limit :lim
    """)
    rows = db.execute(q, {"ids": node_ids, "lim": limit}).fetchall()
    edges = []
    nodes: Set[int] = set(node_ids)
    for r in rows:
        edges.append({"id": r[0], "src": r[1], "dst": r[2], "kind": r[3]})
        nodes.add(r[1]); nodes.add(r[2])
    if not nodes:
        return {"nodes": [], "edges": []}
    nrows = db.execute(text("select id, name, kind from entities where id = any(:ids)"), {"ids": list(nodes)}).fetchall()
    nlist = [{"id": n[0], "name": n[1], "kind": n[2]} for n in nrows]
    return {"nodes": nlist, "edges": edges}

@router.get('/expand')
def expand(entity_id: int, depth: int = 1, limit: int = 200, db: Session = Depends(get_db)):
    frontier = [entity_id]
    seen: Set[int] = set([entity_id])
    all_edges: List[Dict[str, Any]] = []
    all_nodes: Dict[int, Dict[str, Any]] = {}
    for _ in range(max(1, depth)):
        layer = fetch_neighbors(db, frontier, limit)
        all_edges.extend(layer["edges"])
        for n in layer["nodes"]:
            all_nodes[n["id"]] = n
        new_frontier = []
        for e in layer["edges"]:
            for nid in (e["src"], e["dst"]):
                if nid not in seen:
                    seen.add(nid)
                    new_frontier.append(nid)
        frontier = new_frontier
        if not frontier:
            break
    return {"nodes": list(all_nodes.values()), "edges": all_edges}

@router.get('/path')
def pathfind(src: int, dst: int, max_hops: int = 4, db: Session = Depends(get_db)):
    if src == dst:
        return {"path": [src]}
    from collections import deque, defaultdict
    graph = defaultdict(list)
    rows = db.execute(text("select src_entity_id, dst_entity_id from relationships limit 5000")).fetchall()
    for a,b in rows:
        graph[a].append(b)
        graph[b].append(a)
    q = deque([src]); prev = {src: None}
    hops = {src: 0}
    while q:
        u = q.popleft()
        if hops[u] >= max_hops: continue
        for v in graph.get(u, []):
            if v not in prev:
                prev[v] = u
                hops[v] = hops[u] + 1
                if v == dst:
                    # reconstruct
                    path = [dst]
                    while path[-1] is not None:
                        p = prev[path[-1]]
                        if p is None: break
                        path.append(p)
                    path.reverse()
                    return {"path": path}
                q.append(v)
    return {"path": []}

@router.get('/export')
def export(entity_id: int, depth: int = 2, db: Session = Depends(get_db)):
    data = expand(entity_id=entity_id, depth=depth, db=db)
    return data

@router.get('/related')
def related(entity_id: int, limit: int = 20, db: Session = Depends(get_db)):
    # Rank by evidence count, recency, frequency, degree (centrality proxy)
    rows = db.execute(text("""
        with rels as (
          select r.id, case when r.src_entity_id=:id then r.dst_entity_id else r.src_entity_id end as other
          from relationships r where r.src_entity_id=:id or r.dst_entity_id=:id
        ), ev as (
          select re.relationship_id, count(*) as ev_cnt
          from relationship_evidence re
          group by re.relationship_id
        ), deg as (
          select e.id, (select count(*) from relationships rr where rr.src_entity_id=e.id or rr.dst_entity_id=e.id) as degree
          from entities e
        )
        select rels.other as entity_id,
               coalesce(ev.ev_cnt,0) as evidence,
               coalesce(deg.degree,0) as degree
        from rels left join ev on ev.relationship_id = rels.id
        left join deg on deg.id = rels.other
    """), {"id": entity_id}).fetchall()
    scores: Dict[int, Dict[str, Any]] = {}
    now = datetime.now(timezone.utc).timestamp()
    for r in rows:
        eid, ev_cnt, degree = r[0], int(r[1] or 0), int(r[2] or 0)
        freq = 1
        score = ev_cnt*3 + degree*0.5 + freq*1
        s = scores.get(eid, {"entity_id": eid, "evidence": 0, "degree": 0, "score": 0})
        s["evidence"] += ev_cnt
        s["degree"] = max(s["degree"], degree)
        s["score"] += score
        scores[eid] = s
    # attach names
    if not scores:
        return {"related": []}
    ids = [k for k in scores.keys()]
    nrows = db.execute(text("select id, name, kind from entities where id = any(:ids)"), {"ids": ids}).fetchall()
    for n in nrows:
        s = scores.get(n[0])
        if s:
            s.update({"name": n[1], "kind": n[2]})
    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)[:limit]
    return {"related": ranked}

@router.get('/edge/evidence')
def edge_evidence(relationship_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        select re.id, re.evidence_ref_id, rd.source_url, rd.created_at
        from relationship_evidence re
        left join evidence_refs er on er.id = re.evidence_ref_id
        left join raw_documents rd on rd.id = er.raw_document_id
        where re.relationship_id=:rid
    """), {"rid": relationship_id}).fetchall()
    return [
        {"id": r[0], "evidence_ref_id": r[1], "source_url": r[2], "ts": r[3].isoformat() if r[3] else None}
        for r in rows
    ]
