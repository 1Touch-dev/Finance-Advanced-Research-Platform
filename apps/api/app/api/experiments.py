"""
Experiment Framework API
Band A Priority #10: A/B experiment framework for templates
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import get_db
import uuid
import hashlib
import random

router = APIRouter(prefix="/experiments", tags=["experiments"])


# ─── Models ─────────────────────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    name: str
    description: str
    page_type: str  # intelligence, stock, company, etc.
    variants: List[dict]  # [{"id": "control", "weight": 50}, {"id": "variant_a", "weight": 50}]
    targeting: Optional[dict] = None  # {"user_tier": ["pro"], "percentage": 100}
    metrics: List[str]  # ["engagement", "conversion", "time_on_page"]


class VariantAssignment(BaseModel):
    experiment_id: str
    variant_id: str
    user_id: str
    assigned_at: str


class MetricEvent(BaseModel):
    experiment_id: str
    variant_id: str
    user_id: str
    metric: str
    value: float
    timestamp: str


# ─── In-Memory Storage ──────────────────────────────────────────────────────

_experiments: Dict[str, dict] = {}
_assignments: Dict[str, dict] = {}  # user_id:experiment_id -> assignment
_events: List[dict] = []


# ─── Helper Functions ───────────────────────────────────────────────────────

def _get_deterministic_bucket(user_id: str, experiment_id: str, buckets: int = 100) -> int:
    """Get a deterministic bucket for a user in an experiment."""
    hash_input = f"{user_id}:{experiment_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    return hash_value % buckets


def _select_variant(experiment: dict, user_id: str) -> str:
    """Select a variant for a user based on weights."""
    bucket = _get_deterministic_bucket(user_id, experiment["id"])

    cumulative = 0
    for variant in experiment["variants"]:
        cumulative += variant["weight"]
        if bucket < cumulative:
            return variant["id"]

    # Fallback to first variant
    return experiment["variants"][0]["id"]


def _calculate_stats(events: List[dict], metric: str) -> dict:
    """Calculate basic statistics for a metric."""
    values = [e["value"] for e in events if e["metric"] == metric]

    if not values:
        return {"count": 0, "mean": None, "min": None, "max": None}

    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "sum": sum(values),
    }


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/create")
def create_experiment(experiment: ExperimentCreate):
    """Create a new experiment."""
    experiment_id = f"exp-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    # Validate weights sum to 100
    total_weight = sum(v["weight"] for v in experiment.variants)
    if total_weight != 100:
        raise HTTPException(400, f"Variant weights must sum to 100, got {total_weight}")

    exp_data = {
        "id": experiment_id,
        "name": experiment.name,
        "description": experiment.description,
        "page_type": experiment.page_type,
        "variants": experiment.variants,
        "targeting": experiment.targeting or {},
        "metrics": experiment.metrics,
        "status": "draft",
        "created_at": now,
        "started_at": None,
        "ended_at": None,
        "results": None,
    }

    _experiments[experiment_id] = exp_data

    return {"id": experiment_id, "status": "draft"}


@router.get("/list")
def list_experiments(status: Optional[str] = None):
    """List all experiments."""
    experiments = list(_experiments.values())

    if status:
        experiments = [e for e in experiments if e["status"] == status]

    return {"experiments": experiments}


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str):
    """Get experiment details."""
    exp = _experiments.get(experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")
    return exp


@router.post("/{experiment_id}/start")
def start_experiment(experiment_id: str):
    """Start an experiment."""
    exp = _experiments.get(experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")

    if exp["status"] != "draft":
        raise HTTPException(400, f"Cannot start experiment in status: {exp['status']}")

    exp["status"] = "running"
    exp["started_at"] = datetime.utcnow().isoformat()

    return {"id": experiment_id, "status": "running"}


@router.post("/{experiment_id}/stop")
def stop_experiment(experiment_id: str):
    """Stop an experiment."""
    exp = _experiments.get(experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")

    if exp["status"] != "running":
        raise HTTPException(400, f"Cannot stop experiment in status: {exp['status']}")

    exp["status"] = "stopped"
    exp["ended_at"] = datetime.utcnow().isoformat()

    # Calculate final results
    exp["results"] = _calculate_experiment_results(experiment_id)

    return {"id": experiment_id, "status": "stopped", "results": exp["results"]}


@router.get("/{experiment_id}/assign")
def get_variant_assignment(experiment_id: str, user_id: str):
    """Get or create variant assignment for a user."""
    exp = _experiments.get(experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")

    if exp["status"] != "running":
        return {"variant_id": None, "reason": f"Experiment not running (status: {exp['status']})"}

    # Check for existing assignment
    assignment_key = f"{user_id}:{experiment_id}"
    if assignment_key in _assignments:
        return _assignments[assignment_key]

    # Check targeting rules
    targeting = exp.get("targeting", {})
    if targeting.get("percentage", 100) < 100:
        bucket = _get_deterministic_bucket(user_id, f"{experiment_id}:targeting")
        if bucket >= targeting["percentage"]:
            return {"variant_id": None, "reason": "User not in experiment population"}

    # Select and store variant
    variant_id = _select_variant(exp, user_id)
    now = datetime.utcnow().isoformat()

    assignment = {
        "experiment_id": experiment_id,
        "variant_id": variant_id,
        "user_id": user_id,
        "assigned_at": now,
    }

    _assignments[assignment_key] = assignment

    return assignment


@router.post("/{experiment_id}/event")
def record_event(experiment_id: str, event: MetricEvent):
    """Record a metric event for an experiment."""
    exp = _experiments.get(experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")

    if event.metric not in exp["metrics"]:
        raise HTTPException(400, f"Invalid metric: {event.metric}")

    event_data = {
        "experiment_id": experiment_id,
        "variant_id": event.variant_id,
        "user_id": event.user_id,
        "metric": event.metric,
        "value": event.value,
        "timestamp": event.timestamp or datetime.utcnow().isoformat(),
    }

    _events.append(event_data)

    return {"recorded": True}


def _calculate_experiment_results(experiment_id: str) -> dict:
    """Calculate results for an experiment."""
    exp = _experiments.get(experiment_id)
    if not exp:
        return {}

    exp_events = [e for e in _events if e["experiment_id"] == experiment_id]
    exp_assignments = {k: v for k, v in _assignments.items() if v["experiment_id"] == experiment_id}

    results = {
        "total_users": len(set(a["user_id"] for a in exp_assignments.values())),
        "total_events": len(exp_events),
        "by_variant": {},
    }

    for variant in exp["variants"]:
        variant_id = variant["id"]
        variant_events = [e for e in exp_events if e["variant_id"] == variant_id]
        variant_users = [a for a in exp_assignments.values() if a["variant_id"] == variant_id]

        results["by_variant"][variant_id] = {
            "users": len(variant_users),
            "events": len(variant_events),
            "metrics": {
                metric: _calculate_stats(variant_events, metric)
                for metric in exp["metrics"]
            },
        }

    return results


@router.get("/{experiment_id}/results")
def get_experiment_results(experiment_id: str):
    """Get current results for an experiment."""
    exp = _experiments.get(experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")

    # Return cached results if stopped
    if exp["status"] == "stopped" and exp["results"]:
        return exp["results"]

    # Calculate live results
    return _calculate_experiment_results(experiment_id)


@router.delete("/{experiment_id}")
def delete_experiment(experiment_id: str):
    """Delete an experiment (only if draft or stopped)."""
    exp = _experiments.get(experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")

    if exp["status"] == "running":
        raise HTTPException(400, "Cannot delete running experiment. Stop it first.")

    del _experiments[experiment_id]

    # Clean up assignments and events
    keys_to_delete = [k for k in _assignments if _assignments[k]["experiment_id"] == experiment_id]
    for k in keys_to_delete:
        del _assignments[k]

    return {"deleted": True}
