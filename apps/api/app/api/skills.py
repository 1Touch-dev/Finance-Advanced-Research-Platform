from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.db.session import get_db
from app.models.base import Base
from app.models.skills import SkillRegistry, SkillRun, SkillArtifact
import os, json

router = APIRouter(prefix="/skills")

ART_DIR = os.getenv("SKILL_ARTIFACT_DIR", "artifacts")
os.makedirs(ART_DIR, exist_ok=True)

@router.get('/status')
def skills_status():
    from app.services.anthropic_client import anthropic_client
    from app.services.openai_client import openai_client
    return {
        "anthropic": {
            "configured": anthropic_client.is_configured(),
            "model": anthropic_client.model if anthropic_client.is_configured() else None,
        },
        "openai": {"configured": openai_client.is_configured()},
    }

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    # seed registry
    skills = [
        ("dcf","v1","internal"),("comps","v1","internal"),("earnings","v1","anthropic"),
        ("one_pager","v1","anthropic"),("ic_memo","v1","anthropic"),("due_diligence","v1","anthropic"),
        ("model_review","v1","anthropic"),("market_research","v1","anthropic")
    ]
    for name,ver,prov in skills:
        if not db.query(SkillRegistry).filter_by(name=name, version=ver).first():
            db.add(SkillRegistry(name=name, version=ver, provider=prov, allowlisted=True))
    db.commit()
    return {"ok": True}

def _estimate_cost_usd(output: dict) -> tuple:
    tokens = (output.get("cost") or {}).get("tokens", 0)
    cost_cents = max(1, int(tokens * 0.003)) if tokens else 5
    return cost_cents, tokens

@router.post('/run')
def run_skill(name: str, version: str = "v1", input: Optional[Dict[str, Any]] = None, require_review: bool = False, workspace_id: int = 1, db: Session = Depends(get_db)):
    reg = db.query(SkillRegistry).filter_by(name=name, version=version).first()
    if not reg or not reg.allowlisted:
        raise HTTPException(403, "skill not available")
    from app.models.models import Workspace
    ws = db.query(Workspace).filter_by(id=workspace_id).first()
    budget = (ws.skill_budget_usd if ws else 100) * 100
    spent = (ws.skill_spend_usd if ws else 0) * 100
    if spent >= budget:
        raise HTTPException(402, "workspace skill budget exceeded")
    adapter = reg.provider
    run = SkillRun(skill_id=reg.id, input=input, adapter=adapter, status='running', review_required=require_review)
    db.add(run); db.commit(); db.refresh(run)
    if adapter == 'internal':
        output = internal_adapter(name, input or {})
    else:
        output = anthropic_adapter(name, input or {})
    cost_cents, tokens = _estimate_cost_usd(output)
    if ws and spent + cost_cents > budget:
        raise HTTPException(402, "workspace skill budget would be exceeded")
    status = 'requires_review' if require_review else 'succeeded'
    if ws:
        ws.skill_spend_usd = int((spent + cost_cents) / 100)
    db.execute(update(SkillRun).where(SkillRun.id==run.id).values(
        output=output, status=status, finished_at=datetime.now(timezone.utc),
        cost_usd=int(cost_cents / 100), token_count=tokens,
    ))
    db.commit()
    # write artifact
    path = os.path.join(ART_DIR, f"run-{run.id}-{name}.json")
    with open(path,'w') as f:
        json.dump(output, f, indent=2)
    db.add(SkillArtifact(run_id=run.id, kind='json', path=path, meta={"name": name}))
    db.commit()
    return {"run_id": run.id, "status": status, "output": output}

@router.get('/runs/{run_id}')
def get_run(run_id: int, db: Session = Depends(get_db)):
    r = db.query(SkillRun).filter_by(id=run_id).first()
    if not r:
        raise HTTPException(404, "not found")
    return {"id": r.id, "status": r.status, "review_required": r.review_required, "adapter": r.adapter, "output": r.output}

# --- Adapters ---

def anthropic_adapter(name: str, inp: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.anthropic_client import anthropic_client
    from app.services.openai_client import openai_client

    prompts = {
        "dcf": "Produce a DCF valuation analysis with assumptions, sensitivity table, and key risks.",
        "comps": "Produce comparable company analysis with peer multiples and relative valuation.",
        "earnings": "Produce an earnings update memo with beat/miss analysis and forward guidance.",
        "one_pager": "Produce a one-page investment summary with thesis, catalysts, and risks.",
        "ic_memo": "Produce an investment committee memo with recommendation and evidence citations.",
        "due_diligence": "Produce a due diligence checklist and findings summary.",
    }
    instruction = prompts.get(name, f"Run specialized financial analysis for skill '{name}'.")
    prompt = f"{instruction}\n\nData bundle:\n{json.dumps(inp, default=str)}"
    system = "You are an expert financial and intelligence research analyst. Provide professional, cited insight."

    if anthropic_client.is_configured():
        try:
            res = anthropic_client.analyze_text(prompt, system)
            return {
                "provider": "anthropic",
                "skill": name,
                "input": inp,
                "result": res.get("text"),
                "cost": {"tokens": res.get("tokens", 0), "model": res.get("model")},
            }
        except Exception as e:
            if openai_client.is_configured():
                res = openai_client.analyze_text(prompt, system)
                return {
                    "provider": "openai",
                    "skill": name,
                    "input": inp,
                    "result": res,
                    "cost": {"tokens": 0},
                    "anthropic_error": str(e),
                }
            raise HTTPException(502, f"Anthropic skill failed: {e}") from e
    if openai_client.is_configured():
        res = openai_client.analyze_text(prompt, system)
        return {"provider": "openai", "skill": name, "input": inp, "result": res, "cost": {"tokens": 0}}
    return {"provider": "simulated", "skill": name, "input": inp, "result": f"Simulated {name} report (no AI provider configured)."}

def internal_adapter(name: str, inp: Dict[str, Any]) -> Dict[str, Any]:
    # route to internal computations where applicable
    if name == 'dcf':
        from finance.dcf import dcf
        fcf = inp.get('fcf', [10,11,12,13,14]); wacc = float(inp.get('wacc', 0.1)); g = float(inp.get('terminal_growth', 0.02))
        return {"dcf": dcf(fcf, wacc, g), "assumptions": {"fcf": fcf, "wacc": wacc, "g": g}}
    if name == 'comps':
        from finance.comps import multiples
        return {"comps": multiples(inp.get('peers', []))}
    # default stub
    return {"provider": "internal", "skill": name, "input": inp, "result": f"Simulated {name} output."}
