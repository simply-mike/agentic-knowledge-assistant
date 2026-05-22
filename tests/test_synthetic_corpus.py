from pathlib import Path

from app.ingestion.loaders import parse_frontmatter


EXPECTED_SYNTHETIC_DOCS = {
    "cloud_platform_onboarding.md",
    "confidential_metrics_policy.md",
    "data_platform_overview.md",
    "feature_store_access_policy.md",
    "incident_response_playbook.md",
    "kafka_ingestion_runbook.md",
    "metrics_api_reference.md",
    "model_serving_sla.md",
    "object_storage_data_lake_guide.md",
    "spark_job_troubleshooting.md",
}


def test_synthetic_corpus_has_expected_documents() -> None:
    paths = {path.name for path in Path("data/synthetic").glob("*.md")}

    assert paths == EXPECTED_SYNTHETIC_DOCS


def test_synthetic_documents_are_marked_synthetic_internal() -> None:
    for path in Path("data/synthetic").glob("*.md"):
        metadata, content = parse_frontmatter(path.read_text(encoding="utf-8"))

        assert metadata["source"] == "synthetic_internal"
        assert metadata["synthetic"] is True
        assert content.strip()
