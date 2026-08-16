"""
Tests for Narrative Model API (G1, G2)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestModelManagement:
    """Tests for model management endpoints."""

    def test_list_models(self):
        """Test listing available models."""
        response = client.get("/narrative-model/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "recommended" in data
        assert len(data["models"]) > 0

    def test_list_datasets(self):
        """Test listing training datasets."""
        response = client.get("/narrative-model/datasets")
        assert response.status_code == 200
        data = response.json()
        assert "datasets" in data
        assert len(data["datasets"]) > 0


class TestTraining:
    """Tests for training endpoints."""

    def test_start_training(self):
        """Test starting a training job."""
        response = client.post("/narrative-model/train?base_model=base_llama_7b&dataset_id=narratives_v1")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["base_model"] == "base_llama_7b"
        assert data["dataset_id"] == "narratives_v1"
        assert "config" in data

    def test_get_training_status(self):
        """Test getting training status."""
        # First create a job
        create_res = client.post("/narrative-model/train?base_model=base_llama_7b&dataset_id=narratives_v1")
        job_id = create_res.json()["job_id"]

        response = client.get(f"/narrative-model/train/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data

    def test_get_training_metrics(self):
        """Test getting training metrics."""
        response = client.get("/narrative-model/train/test_job/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "train_loss" in data["metrics"]
        assert "eval_loss" in data["metrics"]


class TestDeployment:
    """Tests for deployment endpoints."""

    def test_deploy_model(self):
        """Test deploying a model."""
        response = client.post("/narrative-model/deploy?model_id=finance_narrative_v1")
        assert response.status_code == 200
        data = response.json()
        assert "deployment_id" in data
        assert data["model_id"] == "finance_narrative_v1"
        assert "endpoint" in data

    def test_get_deployment_status(self):
        """Test getting deployment status."""
        response = client.get("/narrative-model/deploy/deploy_123")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "health" in data


class TestGeneration:
    """Tests for narrative generation."""

    def test_generate_analysis(self):
        """Test generating analysis narrative."""
        response = client.post("/narrative-model/generate?ticker=NVDA&report_type=analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "narrative" in data
        assert "confidence" in data

    def test_generate_summary(self):
        """Test generating summary narrative."""
        response = client.post("/narrative-model/generate?ticker=AAPL&report_type=summary")
        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "summary"

    def test_get_performance(self):
        """Test getting model performance."""
        response = client.get("/narrative-model/performance")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "comparison_to_base" in data
