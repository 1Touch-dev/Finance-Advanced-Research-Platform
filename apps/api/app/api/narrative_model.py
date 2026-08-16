"""
Narrative Model API (G1, G2)
Fine-tune and deploy narrative generation models
"""
from fastapi import APIRouter, Query, Body
from typing import Optional, Dict, Any

from app.services.narrative_model_service import (
    get_available_models,
    start_training_job,
    get_training_status,
    get_training_metrics,
    deploy_model,
    get_deployment_status,
    generate_narrative,
    get_model_performance,
    list_training_datasets,
)

router = APIRouter(prefix="/narrative-model", tags=["Narrative Model"])


@router.get("/models")
async def list_models():
    """Get available base models for fine-tuning."""
    return get_available_models()


@router.get("/datasets")
async def list_datasets():
    """List available training datasets."""
    return list_training_datasets()


@router.post("/train")
async def start_training(
    base_model: str = Query(..., description="Base model ID"),
    dataset_id: str = Query(..., description="Training dataset ID"),
    config: Optional[Dict[str, Any]] = Body(None, description="Training config")
):
    """Start model fine-tuning job (requires GPU)."""
    return start_training_job(base_model, dataset_id, config)


@router.get("/train/{job_id}")
async def training_status(job_id: str):
    """Get training job status."""
    return get_training_status(job_id)


@router.get("/train/{job_id}/metrics")
async def training_metrics(job_id: str):
    """Get detailed training metrics."""
    return get_training_metrics(job_id)


@router.post("/deploy")
async def deploy(
    model_id: str = Query(..., description="Model ID to deploy"),
    config: Optional[Dict[str, Any]] = Body(None, description="Deployment config")
):
    """Deploy trained model to production."""
    return deploy_model(model_id, config)


@router.get("/deploy/{deployment_id}")
async def deployment_status(deployment_id: str):
    """Get deployment status."""
    return get_deployment_status(deployment_id)


@router.post("/generate")
async def generate(
    ticker: str = Query(..., description="Stock ticker"),
    report_type: str = Query("analysis", description="Type: analysis, summary, risk")
):
    """Generate narrative using deployed model."""
    return generate_narrative(ticker, report_type)


@router.get("/performance")
async def model_performance():
    """Get model performance metrics."""
    return get_model_performance()
