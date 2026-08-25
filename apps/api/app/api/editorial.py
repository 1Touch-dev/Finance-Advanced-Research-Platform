"""
Editorial Workflow API
Band A Priority #8: Editorial workflow for AI content
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.security import get_current_user
import uuid

router = APIRouter(prefix="/editorial", tags=["editorial"])


# ─── Models ─────────────────────────────────────────────────────────────────

class ContentSubmission(BaseModel):
    content_type: str  # intelligence_report, company_summary, analysis
    entity_id: Optional[str]
    title: str
    content: str
    generated_by: str  # ai, human, hybrid
    metadata: Optional[dict] = None


class ReviewAction(BaseModel):
    action: str  # approve, reject, request_changes
    reviewer_id: str
    comments: Optional[str] = None
    changes_requested: Optional[List[str]] = None


class ContentItem(BaseModel):
    id: str
    content_type: str
    title: str
    status: str
    generated_by: str
    created_at: str
    reviewed_at: Optional[str]
    reviewer_id: Optional[str]
    published_at: Optional[str]


# ─── Workflow States ────────────────────────────────────────────────────────

WORKFLOW_STATES = {
    "draft": {"next": ["pending_review", "archived"]},
    "pending_review": {"next": ["approved", "rejected", "changes_requested"]},
    "changes_requested": {"next": ["pending_review", "archived"]},
    "approved": {"next": ["published", "archived"]},
    "rejected": {"next": ["draft", "archived"]},
    "published": {"next": ["archived", "unpublished"]},
    "unpublished": {"next": ["published", "archived"]},
    "archived": {"next": []},
}


# ─── In-Memory Storage ──────────────────────────────────────────────────────

_content_queue: Dict[str, dict] = {}
_review_history: List[dict] = []


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/submit")
def submit_content(submission: ContentSubmission, current_user: dict = Depends(get_current_user)):
    """Submit AI-generated content for review."""
    content_id = f"content-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    content = {
        "id": content_id,
        "content_type": submission.content_type,
        "entity_id": submission.entity_id,
        "title": submission.title,
        "content": submission.content,
        "generated_by": submission.generated_by,
        "metadata": submission.metadata or {},
        "status": "pending_review",
        "created_at": now,
        "updated_at": now,
        "reviewed_at": None,
        "reviewer_id": None,
        "review_comments": None,
        "published_at": None,
        "version": 1,
        "history": [],
    }

    _content_queue[content_id] = content

    return {
        "id": content_id,
        "status": "pending_review",
        "message": "Content submitted for review",
    }


@router.get("/queue")
def get_review_queue(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 50,
):
    """Get content awaiting review."""
    items = list(_content_queue.values())

    # Default to pending_review if no status specified
    if status:
        items = [i for i in items if i["status"] == status]
    else:
        items = [i for i in items if i["status"] == "pending_review"]

    if content_type:
        items = [i for i in items if i["content_type"] == content_type]

    # Sort by created_at (oldest first for FIFO review)
    items.sort(key=lambda x: x["created_at"])

    return {
        "items": [
            ContentItem(
                id=i["id"],
                content_type=i["content_type"],
                title=i["title"],
                status=i["status"],
                generated_by=i["generated_by"],
                created_at=i["created_at"],
                reviewed_at=i["reviewed_at"],
                reviewer_id=i["reviewer_id"],
                published_at=i["published_at"],
            )
            for i in items[:limit]
        ],
        "total": len(items),
    }


@router.get("/content/{content_id}")
def get_content(content_id: str):
    """Get full content details."""
    content = _content_queue.get(content_id)
    if not content:
        raise HTTPException(404, "Content not found")
    return content


@router.post("/content/{content_id}/review")
def review_content(content_id: str, action: ReviewAction, current_user: dict = Depends(get_current_user)):
    """Review content and take action."""
    content = _content_queue.get(content_id)
    if not content:
        raise HTTPException(404, "Content not found")

    current_status = content["status"]

    # Validate action is allowed from current state
    if action.action == "approve" and current_status not in ["pending_review"]:
        raise HTTPException(400, f"Cannot approve from status: {current_status}")
    if action.action == "reject" and current_status not in ["pending_review"]:
        raise HTTPException(400, f"Cannot reject from status: {current_status}")
    if action.action == "request_changes" and current_status not in ["pending_review"]:
        raise HTTPException(400, f"Cannot request changes from status: {current_status}")

    now = datetime.utcnow().isoformat()

    # Save current state to history
    content["history"].append({
        "status": current_status,
        "changed_at": now,
        "changed_by": action.reviewer_id,
        "action": action.action,
        "comments": action.comments,
    })

    # Update status
    if action.action == "approve":
        content["status"] = "approved"
    elif action.action == "reject":
        content["status"] = "rejected"
    elif action.action == "request_changes":
        content["status"] = "changes_requested"
        content["changes_requested"] = action.changes_requested

    content["reviewed_at"] = now
    content["reviewer_id"] = action.reviewer_id
    content["review_comments"] = action.comments
    content["updated_at"] = now

    # Log review
    _review_history.append({
        "content_id": content_id,
        "action": action.action,
        "reviewer_id": action.reviewer_id,
        "timestamp": now,
    })

    return {
        "id": content_id,
        "status": content["status"],
        "message": f"Content {action.action}d",
    }


@router.post("/content/{content_id}/publish")
def publish_content(content_id: str, publisher_id: str, current_user: dict = Depends(get_current_user)):
    """Publish approved content."""
    content = _content_queue.get(content_id)
    if not content:
        raise HTTPException(404, "Content not found")

    if content["status"] != "approved":
        raise HTTPException(400, f"Cannot publish from status: {content['status']}. Must be approved first.")

    now = datetime.utcnow().isoformat()

    content["status"] = "published"
    content["published_at"] = now
    content["published_by"] = publisher_id
    content["updated_at"] = now

    content["history"].append({
        "status": "published",
        "changed_at": now,
        "changed_by": publisher_id,
        "action": "publish",
    })

    return {
        "id": content_id,
        "status": "published",
        "published_at": now,
    }


@router.post("/content/{content_id}/resubmit")
def resubmit_content(content_id: str, updated_content: str, submitter_id: str, current_user: dict = Depends(get_current_user)):
    """Resubmit content after changes requested."""
    content = _content_queue.get(content_id)
    if not content:
        raise HTTPException(404, "Content not found")

    if content["status"] not in ["changes_requested", "rejected", "draft"]:
        raise HTTPException(400, f"Cannot resubmit from status: {content['status']}")

    now = datetime.utcnow().isoformat()

    content["history"].append({
        "status": content["status"],
        "changed_at": now,
        "changed_by": submitter_id,
        "action": "resubmit",
        "previous_content": content["content"][:500],  # Store snippet of old content
    })

    content["content"] = updated_content
    content["status"] = "pending_review"
    content["version"] += 1
    content["updated_at"] = now
    content["changes_requested"] = None

    return {
        "id": content_id,
        "status": "pending_review",
        "version": content["version"],
    }


@router.get("/stats")
def get_editorial_stats():
    """Get editorial workflow statistics."""
    items = list(_content_queue.values())

    stats = {
        "total": len(items),
        "by_status": {},
        "by_type": {},
        "by_generator": {},
        "avg_review_time_hours": None,
        "recent_reviews": len([r for r in _review_history if r["timestamp"] > (datetime.utcnow() - __import__("datetime").timedelta(days=1)).isoformat()]),
    }

    review_times = []

    for item in items:
        # Count by status
        status = item["status"]
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # Count by type
        ctype = item["content_type"]
        stats["by_type"][ctype] = stats["by_type"].get(ctype, 0) + 1

        # Count by generator
        gen = item["generated_by"]
        stats["by_generator"][gen] = stats["by_generator"].get(gen, 0) + 1

        # Calculate review time
        if item["reviewed_at"]:
            created = datetime.fromisoformat(item["created_at"])
            reviewed = datetime.fromisoformat(item["reviewed_at"])
            review_times.append((reviewed - created).total_seconds() / 3600)

    if review_times:
        stats["avg_review_time_hours"] = round(sum(review_times) / len(review_times), 2)

    return stats


@router.get("/history")
def get_review_history(limit: int = 100):
    """Get recent review history."""
    return {"history": _review_history[-limit:]}
