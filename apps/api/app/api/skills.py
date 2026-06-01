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

@router.post('/run')
def run_skill(name: str, version: str = "v1", input: Optional[Dict[str, Any]] = None, require_review: bool = False, db: Session = Depends(get_db)):
    reg = db.query(SkillRegistry).filter_by(name=name, version=version).first()
    if not reg or not reg.allowlisted:
        raise HTTPException(403, "skill not available")
    adapter = reg.provider
    run = SkillRun(skill_id=reg.id, input=input, adapter=adapter, status='running', review_required=require_review)
    db.add(run); db.commit(); db.refresh(run)
    # invoke adapter
    if adapter == 'internal':
        output = internal_adapter(name, input or {})
    else:
        output = anthropic_adapter(name, input or {})
    status = 'requires_review' if require_review else 'succeeded'
    db.execute(update(SkillRun).where(SkillRun.id==run.id).values(output=output, status=status, finished_at=datetime.now(timezone.utc)))
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
    # Call OpenAI client to perform real GPT-4o structured completions
    from app.services.openai_client import openai_client
    if openai_client.is_configured():
        prompt = f"Run specialized analysis for skill '{name}' using the following data bundle: {json.dumps(inp)}. Provide professional investment committee level insight."
        system_instruction = "You are an expert financial and intelligence research analyst. Provide high-quality, professional cited insight."
        res = openai_client.analyze_text(prompt, system_instruction)
        return {"provider": "openai", "skill": name, "input": inp, "result": res}
    return {"provider": "openai", "skill": name, "input": inp, "result": f"Simulated {name} report (OpenAI - unconfigured)."}

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
