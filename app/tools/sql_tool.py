import re
from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class UnsafeSQLQueryError(ValueError):
    pass


FORBIDDEN_SQL_PATTERNS = (
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\btruncate\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bcopy\b",
    r"\bexecute\b",
    r"\bcall\b",
    r"\bmerge\b",
    r"\bvacuum\b",
    r"\bset\b",
    r"\breset\b",
    r"\bcommit\b",
    r"\brollback\b",
)

ALLOWED_TABLES = {"pipeline_runs"}


class ReadOnlySQLTool:
    def __init__(self, db: "Session", max_rows: int = 50) -> None:
        if max_rows <= 0:
            raise ValueError("max_rows must be positive.")
        self.db = db
        self.max_rows = max_rows

    def run(self, sql_query: str) -> dict[str, Any]:
        from sqlalchemy import text

        validate_read_only_sql(sql_query)
        limited_query = _ensure_limit(sql_query, self.max_rows)
        result = self.db.execute(text(limited_query))
        rows = [dict(row) for row in result.mappings().all()]
        return {
            "sql": limited_query,
            "row_count": len(rows),
            "rows": [_serialize_row(row) for row in rows],
        }


def validate_read_only_sql(sql_query: str) -> None:
    normalized = _normalize_sql(sql_query)
    if not normalized:
        raise UnsafeSQLQueryError("SQL query is empty.")
    if ";" in normalized:
        raise UnsafeSQLQueryError("Multiple statements are not allowed.")
    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        raise UnsafeSQLQueryError("SQL comments are not allowed.")
    if not re.match(r"^select\b", normalized, flags=re.IGNORECASE):
        raise UnsafeSQLQueryError("Only SELECT queries are allowed.")
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            raise UnsafeSQLQueryError("Only read-only SELECT queries are allowed.")
    table_names = set(
        re.findall(
            r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    table_names.update(
        re.findall(
            r"\bjoin\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    if not table_names:
        raise UnsafeSQLQueryError("Query must read from an allowed demo table.")
    if table_names - ALLOWED_TABLES:
        raise UnsafeSQLQueryError("Query references a table outside the demo allowlist.")


def build_pipeline_runs_query(user_query: str) -> str:
    pipeline_name = _infer_pipeline_name(user_query)
    status_filter = _infer_status_filter(user_query)
    select_columns = (
        "pipeline_name, started_at, finished_at, status, "
        "records_processed, latency_ms, error_code"
    )
    where_clauses = [f"pipeline_name = '{_quote_literal(pipeline_name)}'"]
    if status_filter:
        where_clauses.append(f"status = '{_quote_literal(status_filter)}'")
    where_sql = " AND ".join(where_clauses)
    return (
        f"SELECT {select_columns} FROM pipeline_runs "
        f"WHERE {where_sql} ORDER BY started_at DESC LIMIT 10"
    )


def _infer_pipeline_name(user_query: str) -> str:
    normalized = user_query.lower()
    if "spark" in normalized or "feature" in normalized:
        return "spark_feature_jobs"
    if "serving" in normalized or "model" in normalized:
        return "model_serving"
    return "kafka_ingestion"


def _infer_status_filter(user_query: str) -> str | None:
    normalized = user_query.lower()
    if "fail" in normalized or "error" in normalized:
        return "failed"
    if "success" in normalized or "succeeded" in normalized:
        return "succeeded"
    return None


def _ensure_limit(sql_query: str, max_rows: int) -> str:
    normalized = _normalize_sql(sql_query)
    limit_match = re.search(r"\blimit\s+(\d+)\b", normalized, flags=re.IGNORECASE)
    if limit_match:
        requested_limit = int(limit_match.group(1))
        capped_limit = min(requested_limit, max_rows)
        return (
            f"{normalized[: limit_match.start()]}LIMIT {capped_limit}"
            f"{normalized[limit_match.end() :]}"
        )
    return f"{normalized} LIMIT {max_rows}"


def _normalize_sql(sql_query: str) -> str:
    return " ".join(sql_query.strip().split())


def _quote_literal(value: str) -> str:
    return value.replace("'", "''")


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize_value(value) for key, value in row.items()}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return value
