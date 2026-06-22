"""
RAG Chat API — per-entity cited Q&A using intelligence report data.

POST /chat/ask
  body: { report_id, question, history? }
  → { answer, sources, context_used, entity_name }

POST /chat/summary/{report_id}
  → { summary }
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.intelligence_service import get_intelligence_report

try:
    from app.services.rag_chat_service import answer_question, build_entity_summary
    _RAG_OK = True
except ImportError:
    _RAG_OK = False

router = APIRouter(prefix="/chat", tags=["RAG Chat"])


class ChatMessage(BaseModel):
    role:    str  # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    report_id: Optional[int] = None
    question:  str
    entity_name: Optional[str] = None
    history:   Optional[List[ChatMessage]] = None


@router.post("/ask")
def chat_ask(payload: AskRequest, db: Session = Depends(get_db)):
    """
    Ask a natural-language question about an intelligence report.
    - If report_id is provided: answers from that specific report's data.
    - If entity_name only: builds a stub context and answers from general knowledge + entity name.
    Returns a cited answer with supporting evidence sources.
    """
    if not _RAG_OK:
        raise HTTPException(503, "RAG chat service not available")

    report = None
    if payload.report_id:
        report = get_intelligence_report(db, payload.report_id)
        if not report:
            raise HTTPException(404, f"Report #{payload.report_id} not found")

    history = [{"role": m.role, "content": m.content} for m in (payload.history or [])]
    result  = answer_question(payload.question, report, chat_history=history, entity_name=payload.entity_name)
    return result


@router.post("/summary/{report_id}")
def chat_summary(report_id: int, db: Session = Depends(get_db)):
    """
    Generate a 3-sentence executive summary for an entity's intelligence report.
    """
    if not _RAG_OK:
        raise HTTPException(503, "RAG chat service not available")

    report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, f"Report #{report_id} not found")

    summary = build_entity_summary(report)
    return {
        "report_id":   report_id,
        "entity_name": report.get("entity_name"),
        "summary":     summary,
    }
