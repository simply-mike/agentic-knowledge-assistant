import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text

from app.config import get_settings
from app.db.models import Base, PipelineRun
from app.db.session import engine
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


def init_db() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    with engine.begin() as connection:
        logger.info("enabling_pgvector_extension")
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        logger.info("creating_database_tables")
        Base.metadata.create_all(bind=connection)

    with engine.begin() as connection:
        _seed_pipeline_runs(connection)

    logger.info("database_initialized")


def _seed_pipeline_runs(connection) -> None:
    existing_count = connection.execute(select(func.count()).select_from(PipelineRun)).scalar_one()
    if existing_count:
        logger.info("demo_pipeline_runs_already_seeded", extra={"count": existing_count})
        return

    now = datetime.now(UTC).replace(microsecond=0)
    rows = [
        {
            "pipeline_name": "kafka_ingestion",
            "started_at": now - timedelta(hours=2),
            "finished_at": now - timedelta(hours=1, minutes=52),
            "status": "succeeded",
            "records_processed": 1_240_000,
            "latency_ms": 175,
            "error_code": None,
        },
        {
            "pipeline_name": "kafka_ingestion",
            "started_at": now - timedelta(hours=7),
            "finished_at": now - timedelta(hours=6, minutes=52),
            "status": "failed",
            "records_processed": 480_000,
            "latency_ms": 610,
            "error_code": "KAFKA_TIMEOUT",
        },
        {
            "pipeline_name": "spark_feature_jobs",
            "started_at": now - timedelta(hours=3),
            "finished_at": now - timedelta(hours=2, minutes=38),
            "status": "succeeded",
            "records_processed": 820_000,
            "latency_ms": 740,
            "error_code": None,
        },
        {
            "pipeline_name": "model_serving",
            "started_at": now - timedelta(hours=1),
            "finished_at": now - timedelta(minutes=56),
            "status": "succeeded",
            "records_processed": 96_000,
            "latency_ms": 88,
            "error_code": None,
        },
    ]
    connection.execute(PipelineRun.__table__.insert(), rows)
    logger.info("demo_pipeline_runs_seeded", extra={"count": len(rows)})


if __name__ == "__main__":
    init_db()
