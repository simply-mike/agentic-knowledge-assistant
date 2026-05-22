from pathlib import Path

from app.ingestion.loaders import parse_frontmatter


EXPECTED_PUBLIC_MWS_DOCS = {
    "mws_cloud_platform_overview.md",
    "mws_data_kafka_ingestion.md",
    "mws_data_lakehouse_overview.md",
    "mws_managed_kafka_overview.md",
    "mws_managed_kafka_sla.md",
    "mws_object_storage_access.md",
    "mws_object_storage_overview.md",
}


def test_public_mws_corpus_has_expected_documents() -> None:
    paths = {path.name for path in Path("data/raw/public_mws").glob("*.md")}

    assert paths == EXPECTED_PUBLIC_MWS_DOCS


def test_public_mws_documents_are_public_and_not_synthetic() -> None:
    for path in Path("data/raw/public_mws").glob("*.md"):
        metadata, content = parse_frontmatter(path.read_text(encoding="utf-8"))

        assert metadata["source"] == "public_mws_docs"
        assert metadata["permission_level"] == "public"
        assert metadata["synthetic"] is False
        assert str(metadata["url"]).startswith(("https://mws.ru/", "https://docs.data.mws.ru/"))
        assert content.strip()
