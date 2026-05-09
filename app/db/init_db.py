import logging

from sqlalchemy import text

from app.config import get_settings
from app.db.models import Base
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

    logger.info("database_initialized")


if __name__ == "__main__":
    init_db()
