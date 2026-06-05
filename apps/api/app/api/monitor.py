from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, update
from typing import Optional, List
import csv, io, json, os, requests
from app.db.session import get_db
from app.models.base import Base
from app.models.monitor import Watchlist, WatchlistItem, Portfolio, Position, AlertRule, AlertEvent, DeliveryChannel

router = APIRouter(prefix="/monitor")

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {"ok": True}

# --- Watchlists ---
@router.post('/watchlists')
def create_watchlist(name: str, db: Session = Depends(get_db)):
    w = Watchlist(name=name); db.add(w); db.commit(); db.refresh(w); return {"id": w.id}

@router.post('/watchlists/{wid}/items')
def add_watch_item(wid: int, entity_id: Optional[int] = None, ticker: Optional[str] = None, notes: Optional[str] = None, db: Session = Depends(get_db)):
    i = WatchlistItem(watchlist_id=wid, entity_id=entity_id, ticker=ticker, notes=notes); db.add(i); db.commit(); db.refresh(i); return {"id": i.id}

@router.get('/watchlists/{wid}')
def get_watchlist(wid: int, db: Session = Depends(get_db)):
    w = db.query(Watchlist).filter_by(id=wid).first();
    if not w: raise HTTPException(404, 'not found')
    items = db.execute(text("select id,entity_id,ticker,notes from watchlist_items where watchlist_id=:id"), {"id": wid}).fetchall()
    return {"id": w.id, "name": w.name, "items": [{"id": r[0], "entity_id": r[1], "ticker": r[2], "notes": r[3]} for r in items]}

# --- Portfolios ---
@router.post('/portfolios')
def create_portfolio(name: str, base_ccy: str = 'USD', thesis: Optional[str] = None, db: Session = Depends(get_db)):
    p = Portfolio(name=name, base_ccy=base_ccy, thesis=thesis); db.add(p); db.commit(); db.refresh(p); return {"id": p.id}

@router.post('/portfolios/{pid}/positions')
def add_position(pid: int, ticker: str, qty: float, cost_basis: float, entity_id: Optional[int] = None, notes: Optional[str] = None, db: Session = Depends(get_db)):
    pos = Position(portfolio_id=pid, ticker=ticker, qty=qty, cost_basis=cost_basis, entity_id=entity_id, notes=notes); db.add(pos); db.commit(); db.refresh(pos); return {"id": pos.id}

@router.post('/portfolios/{pid}/import_csv')
def import_csv(pid: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = file.file.read().decode('utf-8'); reader = csv.DictReader(io.StringIO(content))
    count=0
    for row in reader:
        db.add(Position(portfolio_id=pid, ticker=row.get('ticker'), qty=float(row.get('qty',0)), cost_basis=float(row.get('cost_basis',0)), notes=row.get('notes')))
        count+=1
    db.commit(); return {"imported": count}

@router.get('/portfolios/{pid}/exposure')
def exposure(pid: int, db: Session = Depends(get_db)):
    rows = db.execute(text("select ticker, sum(qty) as qty, avg(cost_basis) as cb from positions where portfolio_id=:id group by ticker"), {"id": pid}).fetchall()
    total = sum((r[1] or 0)*(r[2] or 0) for r in rows)
    breakdown = [{"ticker": r[0], "qty": r[1], "cost_basis": r[2], "weight": (((r[1] or 0)*(r[2] or 0))/total if total else 0)} for r in rows]
    return {"total_cost": total, "breakdown": breakdown}

# --- Alerts ---
@router.post('/rules')
def create_rule(name: str, kind: str, params: Optional[dict] = None, watchlist_id: Optional[int] = None, portfolio_id: Optional[int] = None, db: Session = Depends(get_db)):
    r = AlertRule(name=name, kind=kind, params=params or {}, watchlist_id=watchlist_id, portfolio_id=portfolio_id)
    db.add(r); db.commit(); db.refresh(r); return {"id": r.id}

@router.post('/rules/{rid}/channels')
def add_channel(rid: int, kind: str, target: Optional[str] = None, meta: Optional[dict] = None, db: Session = Depends(get_db)):
    db.add(DeliveryChannel(rule_id=rid, kind=kind, target=target, meta=meta or {})); db.commit(); return {"ok": True}

@router.post('/scan')
def run_scan(db: Session = Depends(get_db)):
    """Scan for real connector deltas against watchlist entities."""
    rules = db.query(AlertRule).filter_by(enabled=True).all()
    created = []
    seen_keys = set()
    for r in rules:
        k = r.kind
        params = r.params or {}
        if k in ('new_filing', 'filing', 'sec_filing'):
            rows = db.execute(text("""
                select srm.external_id, srm.normalized, s.name
                from source_record_meta srm
                join sources s on s.id = srm.source_id
                where s.kind in ('sec_edgar', 'sec')
                and srm.last_ingested_at > datetime('now', '-24 hours')
                order by srm.last_ingested_at desc limit 20
            """)).fetchall()
            for row in rows:
                key = f"filing-{row[0]}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                ev = AlertEvent(rule_id=r.id, kind='new_filing', ticker=params.get('ticker'), payload={
                    'external_id': row[0], 'source': row[2], 'normalized': row[1],
                })
                db.add(ev)
                db.flush()
                created.append(ev.id)
        elif k in ('new_contract', 'procurement', 'usaspending'):
            rows = db.execute(text("""
                select srm.external_id, srm.normalized
                from source_record_meta srm
                join sources s on s.id = srm.source_id
                where s.kind = 'usaspending'
                and srm.last_ingested_at > datetime('now', '-48 hours')
                limit 10
            """)).fetchall()
            for row in rows:
                key = f"contract-{row[0]}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                ev = AlertEvent(rule_id=r.id, kind='new_contract', ticker=None, payload={
                    'external_id': row[0], 'normalized': row[1],
                })
                db.add(ev)
                db.flush()
                created.append(ev.id)
        elif k == 'sanctions_hit':
            rows = db.execute(text("""
                select srm.external_id, srm.normalized
                from source_record_meta srm
                join sources s on s.id = srm.source_id
                where s.kind = 'ofac'
                and srm.last_ingested_at > datetime('now', '-72 hours')
                limit 5
            """)).fetchall()
            for row in rows:
                key = f"sanctions-{row[0]}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                ev = AlertEvent(rule_id=r.id, kind='sanctions_hit', ticker=None, payload={
                    'external_id': row[0], 'normalized': row[1],
                })
                db.add(ev)
                db.flush()
                created.append(ev.id)
    db.commit()
    return {"events": created, "count": len(created)}

@router.get('/events')
def list_events(delivered: Optional[bool] = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(AlertEvent).order_by(AlertEvent.id.desc())
    if delivered is not None:
        q = q.filter_by(delivered=delivered)
    events = q.limit(limit).all()
    return [{"id": e.id, "rule_id": e.rule_id, "kind": e.kind, "ticker": e.ticker, "payload": e.payload, "delivered": e.delivered} for e in events]

@router.post('/deliver')
def deliver(db: Session = Depends(get_db)):
    events = db.query(AlertEvent).filter_by(delivered=False).all()
    delivered = []
    for ev in events:
        chans = db.query(DeliveryChannel).filter_by(rule_id=ev.rule_id).all()
        for c in chans:
            if c.kind == 'webhook' and c.target:
                try:
                    requests.post(c.target, json={"event": ev.kind, "payload": ev.payload})
                except Exception:
                    pass
            elif c.kind == 'email' and c.target:
                try:
                    from app.services.sendgrid_client import sendgrid_client
                    subject = f"Platform Watchlist Alert: {ev.kind.upper()}"
                    body_html = f"<h3>Watchlist Alert Triggered</h3><p>An alert has been triggered: <strong>{ev.kind}</strong></p><p>Details: {json.dumps(ev.payload)}</p>"
                    sendgrid_client.send_email(c.target, subject, body_html)
                except Exception:
                    pass
            elif c.kind == 'sms' and c.target:
                try:
                    from app.services.twilio_client import twilio_client
                    body = f"Watchlist Alert: {ev.kind.upper()} triggered! Details: {json.dumps(ev.payload)}"
                    twilio_client.send_sms(c.target, body)
                except Exception:
                    pass
            # inapp/slack/teams: Phase 1 stub (recorded via event row)
        ev.delivered = True
        delivered.append(ev.id)
    db.commit(); return {"delivered": delivered}
