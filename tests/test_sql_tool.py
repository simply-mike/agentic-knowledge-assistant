from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.tools.sql_tool import ReadOnlySQLTool, UnsafeSQLQueryError, validate_read_only_sql


def test_sql_tool_allows_read_only_pipeline_runs_query() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as session:
        session.execute(
            text(
                """
                CREATE TABLE pipeline_runs (
                    pipeline_name TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT,
                    records_processed INTEGER,
                    latency_ms INTEGER,
                    error_code TEXT
                )
                """
            )
        )
        session.execute(
            text(
                """
                INSERT INTO pipeline_runs
                VALUES (
                    'kafka_ingestion',
                    '2026-05-15T10:00:00+00:00',
                    '2026-05-15T10:08:00+00:00',
                    'succeeded',
                    1240000,
                    175,
                    NULL
                )
                """
            )
        )
        session.commit()

        result = ReadOnlySQLTool(session).run(
            "SELECT pipeline_name, status, latency_ms FROM pipeline_runs"
        )

    assert result["row_count"] == 1
    assert result["rows"][0]["pipeline_name"] == "kafka_ingestion"


def test_sql_tool_rejects_mutating_queries() -> None:
    for sql_query in (
        "INSERT INTO pipeline_runs VALUES ('x')",
        "UPDATE pipeline_runs SET status = 'failed'",
        "DELETE FROM pipeline_runs",
        "DROP TABLE pipeline_runs",
        "CREATE TABLE unsafe (id int)",
        "TRUNCATE TABLE pipeline_runs",
    ):
        try:
            validate_read_only_sql(sql_query)
        except UnsafeSQLQueryError:
            continue
        raise AssertionError(f"unsafe SQL was accepted: {sql_query}")


def test_sql_tool_rejects_multiple_statements_and_unapproved_tables() -> None:
    for sql_query in (
        "SELECT * FROM pipeline_runs; SELECT * FROM users",
        "SELECT * FROM users",
        "SELECT 1",
        "SELECT * FROM pipeline_runs -- comment",
    ):
        try:
            validate_read_only_sql(sql_query)
        except UnsafeSQLQueryError:
            continue
        raise AssertionError(f"unsafe SQL was accepted: {sql_query}")
