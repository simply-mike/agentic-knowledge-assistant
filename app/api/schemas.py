from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    database: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(default="demo_user")
    role: str
    message: str
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, Any] | None = None


class SourceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str | None = None
    chunk_id: str
    source: str


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    sources: list[SourceSchema]
    tool_calls: list[dict[str, Any]]
    trace_id: str
