from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PipelineMetrics:
    pipeline_name: str
    period: str
    avg_latency_ms: int
    p95_latency_ms: int
    failed_jobs: int
    success_rate: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "period": self.period,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "failed_jobs": self.failed_jobs,
            "success_rate": self.success_rate,
        }


SYNTHETIC_METRICS: dict[tuple[str, str], PipelineMetrics] = {
    ("kafka_ingestion", "last_24h"): PipelineMetrics(
        pipeline_name="kafka_ingestion",
        period="last_24h",
        avg_latency_ms=183,
        p95_latency_ms=420,
        failed_jobs=3,
        success_rate=0.992,
    ),
    ("spark_feature_jobs", "last_24h"): PipelineMetrics(
        pipeline_name="spark_feature_jobs",
        period="last_24h",
        avg_latency_ms=740,
        p95_latency_ms=1320,
        failed_jobs=1,
        success_rate=0.987,
    ),
    ("model_serving", "last_24h"): PipelineMetrics(
        pipeline_name="model_serving",
        period="last_24h",
        avg_latency_ms=92,
        p95_latency_ms=210,
        failed_jobs=0,
        success_rate=0.999,
    ),
}


def mock_metrics_api(pipeline_name: str, period: str = "last_24h") -> dict[str, Any]:
    """Return deterministic synthetic metrics for demo tool-use."""
    normalized_pipeline = _normalize_pipeline_name(pipeline_name)
    normalized_period = _normalize_period(period)
    metrics = SYNTHETIC_METRICS.get((normalized_pipeline, normalized_period))
    if metrics:
        return metrics.as_dict()

    fallback = PipelineMetrics(
        pipeline_name=normalized_pipeline,
        period=normalized_period,
        avg_latency_ms=250,
        p95_latency_ms=620,
        failed_jobs=0,
        success_rate=0.995,
    )
    return fallback.as_dict()


def infer_pipeline_name(query: str) -> str:
    normalized = query.lower()
    if "spark" in normalized or "feature" in normalized:
        return "spark_feature_jobs"
    if "serving" in normalized or "model" in normalized:
        return "model_serving"
    return "kafka_ingestion"


def infer_period(query: str) -> str:
    normalized = query.lower()
    if "24" in normalized or "day" in normalized or "daily" in normalized:
        return "last_24h"
    return "last_24h"


def _normalize_pipeline_name(pipeline_name: str) -> str:
    return pipeline_name.strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_period(period: str) -> str:
    return period.strip().lower().replace("-", "_").replace(" ", "_")
