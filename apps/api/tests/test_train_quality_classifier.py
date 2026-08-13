"""
Tests for app.scripts.train_quality_classifier (Phase 3b training CLI).

Runs the actual script as a subprocess against tiny synthetic label files in
tmp_path — this is the honest way to test a CLI's argument parsing, refusal
behavior, and exit codes without reaching into its internals. No network
dependency; no real OPENAI_API_KEY needed since training only reads
pre-computed labels from a JSONL file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]


def _write_labels(path: Path, rows: list[dict]) -> None:
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _run_train(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "app.scripts.train_quality_classifier", *args],
        cwd=API_ROOT, capture_output=True, text=True, timeout=60,
    )


def _labeled_rows(n_good: int, n_bad: int) -> list[dict]:
    rows = []
    for i in range(n_good):
        rows.append({"judge_ok": True, "judge_publishable": True,
                     "rule_features": {"overall_score": 0.9, "hard_failure_count": 0, "citation_coverage": 0.95}})
    for i in range(n_bad):
        rows.append({"judge_ok": True, "judge_publishable": False,
                     "rule_features": {"overall_score": 0.2, "hard_failure_count": 3, "citation_coverage": 0.1}})
    return rows


def test_refuses_to_train_below_min_samples_by_default(tmp_path):
    labels_path = tmp_path / "labels.jsonl"
    _write_labels(labels_path, _labeled_rows(3, 3))
    result = _run_train("--labels", str(labels_path), "--out", str(tmp_path / "model.joblib"))
    assert result.returncode == 1
    assert "REFUSING to train" in result.stdout
    assert not (tmp_path / "model.joblib").exists()


def test_force_trains_a_demo_model_and_warns(tmp_path):
    labels_path = tmp_path / "labels.jsonl"
    _write_labels(labels_path, _labeled_rows(6, 6))
    out_path = tmp_path / "model.joblib"
    result = _run_train("--labels", str(labels_path), "--force", "--min-samples", "1", "--out", str(out_path))
    assert result.returncode == 0
    assert "WARNING: training with --force" in result.stdout
    assert "demo" in result.stdout.lower()
    assert out_path.exists()

    from app.services.quality.classifier import QualityClassifier
    model = QualityClassifier.load(out_path)
    assert model is not None
    assert "demo" in model.version
    assert model.metrics["n_samples"] == 12


def test_ignores_rows_without_ok_judge_verdict(tmp_path):
    labels_path = tmp_path / "labels.jsonl"
    rows = _labeled_rows(2, 2) + [
        {"judge_ok": False, "judge_publishable": None, "rule_features": {}},
        {"judge_ok": True, "judge_publishable": True, "rule_features": {}},  # empty rule_features -> unusable
    ]
    _write_labels(labels_path, rows)
    result = _run_train("--labels", str(labels_path), "--force", "--min-samples", "1",
                         "--out", str(tmp_path / "model.joblib"))
    assert "4 usable labeled rows" in result.stdout


def test_missing_labels_file_reports_zero_rows(tmp_path):
    result = _run_train("--labels", str(tmp_path / "does_not_exist.jsonl"),
                         "--out", str(tmp_path / "model.joblib"))
    assert result.returncode == 1
    assert "0 usable labeled rows" in result.stdout


def test_refuses_when_only_one_class_present(tmp_path):
    labels_path = tmp_path / "labels.jsonl"
    _write_labels(labels_path, _labeled_rows(10, 0))  # all publishable, no negative class
    result = _run_train("--labels", str(labels_path), "--force", "--min-samples", "1",
                         "--out", str(tmp_path / "model.joblib"))
    assert result.returncode == 1
    assert "both classes present" in result.stdout


def test_merges_multiple_label_files(tmp_path):
    real_path = tmp_path / "real.jsonl"
    synth_path = tmp_path / "synth.jsonl"
    real_rows = [{**r, "source": "live"} for r in _labeled_rows(3, 3)]
    synth_rows = [{**r, "source": "synthetic"} for r in _labeled_rows(3, 3)]
    _write_labels(real_path, real_rows)
    _write_labels(synth_path, synth_rows)

    result = _run_train("--labels", str(real_path), str(synth_path), "--force", "--min-samples", "1",
                         "--out", str(tmp_path / "model.joblib"))
    assert result.returncode == 0
    assert "12 usable labeled rows across 2 file(s)" in result.stdout


def test_reports_source_composition_and_saves_it_in_metrics(tmp_path):
    real_path = tmp_path / "real.jsonl"
    synth_path = tmp_path / "synth.jsonl"
    _write_labels(real_path, [{**r, "source": "live"} for r in _labeled_rows(2, 2)])
    _write_labels(synth_path, [{**r, "source": "synthetic"} for r in _labeled_rows(4, 4)])

    out_path = tmp_path / "model.joblib"
    result = _run_train("--labels", str(real_path), str(synth_path), "--force", "--min-samples", "1",
                         "--out", str(out_path))
    assert result.returncode == 0
    assert "'live': 4" in result.stdout
    assert "'synthetic': 8" in result.stdout

    from app.services.quality.classifier import QualityClassifier
    model = QualityClassifier.load(out_path)
    assert model.metrics["composition"] == {"live": 4, "synthetic": 8}
    assert model.metrics["synthetic_fraction"] == pytest.approx(8 / 12, abs=1e-3)


def test_refuses_when_synthetic_fraction_exceeds_max_without_force(tmp_path):
    real_path = tmp_path / "real.jsonl"
    synth_path = tmp_path / "synth.jsonl"
    _write_labels(real_path, [{**r, "source": "live"} for r in _labeled_rows(1, 1)])
    _write_labels(synth_path, [{**r, "source": "synthetic"} for r in _labeled_rows(20, 20)])

    result = _run_train("--labels", str(real_path), str(synth_path), "--min-samples", "1",
                         "--out", str(tmp_path / "model.joblib"))
    assert result.returncode == 1
    assert "REFUSING to train" in result.stdout
    assert "synthetic" in result.stdout
    assert not (tmp_path / "model.joblib").exists()


def test_force_overrides_synthetic_fraction_refusal(tmp_path):
    real_path = tmp_path / "real.jsonl"
    synth_path = tmp_path / "synth.jsonl"
    _write_labels(real_path, [{**r, "source": "live"} for r in _labeled_rows(1, 1)])
    _write_labels(synth_path, [{**r, "source": "synthetic"} for r in _labeled_rows(20, 20)])

    result = _run_train("--labels", str(real_path), str(synth_path), "--force", "--min-samples", "1",
                         "--out", str(tmp_path / "model.joblib"))
    assert result.returncode == 0
    assert (tmp_path / "model.joblib").exists()

