"""
Narrative Model Service (G1, G2)
Fine-tune and deploy narrative generation models
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.no_data import no_data_response, NoDataReason


def get_available_models() -> Dict[str, Any]:
    """Get available base models for fine-tuning."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response("models", "available_models", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def start_training_job(base_model: str, dataset_id: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Start a model fine-tuning job (requires GPU)."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response(base_model, "training_job", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def get_training_status(job_id: str) -> Dict[str, Any]:
    """Get training job status."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response(job_id, "training_status", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def get_training_metrics(job_id: str) -> Dict[str, Any]:
    """Get detailed training metrics."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response(job_id, "training_metrics", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def deploy_model(model_id: str, deployment_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Deploy trained model to production."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response(model_id, "model_deployment", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def get_deployment_status(deployment_id: str) -> Dict[str, Any]:
    """Get deployment status."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response(deployment_id, "deployment_status", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def generate_narrative(ticker: str, report_type: str = "analysis") -> Dict[str, Any]:
    """Generate narrative using deployed model."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response(ticker, "narrative_generation", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def get_model_performance() -> Dict[str, Any]:
    """Get model performance metrics."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response("model", "performance_metrics", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}


def list_training_datasets() -> Dict[str, Any]:
    """List available training datasets."""
    return {"status": "not_available", "reason": "GPU training infrastructure not configured", **no_data_response("datasets", "training_datasets", NoDataReason.DEPENDENCY_MISSING, details="GPU training infrastructure not configured")}
