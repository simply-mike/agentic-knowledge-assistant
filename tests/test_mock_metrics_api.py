from app.tools.mock_metrics_api import infer_pipeline_name, mock_metrics_api


def test_mock_metrics_api_returns_deterministic_kafka_metrics() -> None:
    result = mock_metrics_api("kafka_ingestion", "last_24h")

    assert result["pipeline_name"] == "kafka_ingestion"
    assert result["p95_latency_ms"] == 420
    assert result["success_rate"] == 0.992


def test_infer_pipeline_name_from_query() -> None:
    assert infer_pipeline_name("What is Spark feature latency?") == "spark_feature_jobs"
    assert infer_pipeline_name("Show Kafka failed jobs") == "kafka_ingestion"
