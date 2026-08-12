"""
Per-request pipeline tracing — makes every RAG stage inspectable.

Attach a Trace to a retrieval/answer call; each stage records timing + a compact
summary (scores, counts, guardrail verdicts). Surfaced via ?debug=true and logged
structured. Zero cost when debug is off (stages are cheap dict appends).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Trace:
    enabled: bool = False
    stages: List[Dict[str, Any]] = field(default_factory=list)
    _t0: float = field(default_factory=time.perf_counter)

    def stage(self, name: str, **data: Any) -> None:
        if not self.enabled:
            return
        self.stages.append({
            "stage": name,
            "elapsed_ms": round((time.perf_counter() - self._t0) * 1000, 2),
            **data,
        })

    def as_dict(self) -> Dict[str, Any]:
        return {"stages": self.stages, "total_ms": round((time.perf_counter() - self._t0) * 1000, 2)}
