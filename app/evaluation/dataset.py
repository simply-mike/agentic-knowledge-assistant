from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


ExpectedBehavior = Literal["answer", "tool_call", "deny_permission", "fallback"]


class EvalQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    role: str
    expected_behavior: ExpectedBehavior
    expected_sources: list[str] = Field(default_factory=list)
    expected_tool: str | None = None
    filters: dict[str, Any] | None = None


def load_eval_questions(path: Path) -> list[EvalQuestion]:
    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, list):
        raise ValueError("Evaluation dataset must be a YAML list of questions.")
    return [EvalQuestion.model_validate(item) for item in raw_data]
