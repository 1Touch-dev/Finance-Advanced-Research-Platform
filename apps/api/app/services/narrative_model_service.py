"""
Narrative Model Service (G1, G2)
Fine-tune and deploy narrative generation models

BLOCKED: No GPU infrastructure available.
All functions return no_data responses until GPU training infrastructure is configured.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.no_data import no_data_response, NoDataReason


def get_available_models() -> Dict[str, Any]:
    """Get available base models for fine-tuning.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity="models",
        data_type="available_models",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def start_training_job(base_model: str, dataset_id: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Start a model fine-tuning job (requires GPU).

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity=base_model,
        data_type="training_job",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def get_training_status(job_id: str) -> Dict[str, Any]:
    """Get training job status.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity=job_id,
        data_type="training_status",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def get_training_metrics(job_id: str) -> Dict[str, Any]:
    """Get detailed training metrics.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity=job_id,
        data_type="training_metrics",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def deploy_model(model_id: str, deployment_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Deploy trained model to production.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity=model_id,
        data_type="model_deployment",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def get_deployment_status(deployment_id: str) -> Dict[str, Any]:
    """Get deployment status.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity=deployment_id,
        data_type="deployment_status",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def generate_narrative(ticker: str, report_type: str = "analysis") -> Dict[str, Any]:
    """Generate narrative using deployed model.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity=ticker,
        data_type="narrative_generation",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def get_model_performance() -> Dict[str, Any]:
    """Get model performance metrics.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity="model",
        data_type="performance_metrics",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )


def list_training_datasets() -> Dict[str, Any]:
    """List available training datasets.

    BLOCKED: No GPU infrastructure.
    Returns no_data response until GPU training infrastructure is configured.
    """
    return no_data_response(
        entity="datasets",
        data_type="training_datasets",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Narrative Model Service",
        details="Narrative model requires GPU infrastructure",
    )
