from dataclasses import dataclass
from typing import Any

from app.evaluation.dataset import EvalQuestion
from app.retrieval.rag import RAGResponse


@dataclass(frozen=True)
class EvaluationCheck:
    name: str
    passed: bool
    details: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass(frozen=True)
class QuestionEvaluation:
    question_id: str
    role: str
    tags: list[str]
    expected_behavior: str
    expected_sources: list[str]
    expected_tool: str | None
    answer_has_citation: bool
    source_hit: bool | None
    permission_correct: bool | None
    tool_call_correct: bool | None
    refusal_correct: bool | None
    called_tools: list[str]
    checks: list[EvaluationCheck]
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "role": self.role,
            "tags": self.tags,
            "expected_behavior": self.expected_behavior,
            "expected_sources": self.expected_sources,
            "expected_tool": self.expected_tool,
            "answer_has_citation": self.answer_has_citation,
            "source_hit": self.source_hit,
            "permission_correct": self.permission_correct,
            "tool_call_correct": self.tool_call_correct,
            "refusal_correct": self.refusal_correct,
            "called_tools": self.called_tools,
            "checks": [check.as_dict() for check in self.checks],
            "passed": self.passed,
        }


def evaluate_response(question: EvalQuestion, response: RAGResponse) -> QuestionEvaluation:
    source_hit = (
        _source_hit(question.expected_sources, response)
        if question.expected_sources
        else None
    )
    called_tools = [
        str(tool_call.get("tool"))
        for tool_call in response.tool_calls
        if tool_call.get("tool") is not None
    ]
    answer_has_citation = bool(response.citations)
    expected_tool = question.expected_tool

    tool_call_correct = None
    if expected_tool:
        tool_call_correct = expected_tool in called_tools

    refusal_expected = question.expected_behavior in {"deny_permission", "fallback"}
    refusal_correct = _is_refusal_like(response.answer) if refusal_expected else None
    permission_correct = None
    if question.expected_behavior == "deny_permission":
        permission_correct = _is_refusal_like(response.answer) and not bool(source_hit)

    checks = _build_checks(
        question=question,
        response=response,
        source_hit=source_hit,
        answer_has_citation=answer_has_citation,
        tool_call_correct=tool_call_correct,
        permission_correct=permission_correct,
        refusal_correct=refusal_correct,
    )

    return QuestionEvaluation(
        question_id=question.id,
        role=question.role,
        tags=question.tags,
        expected_behavior=question.expected_behavior,
        expected_sources=question.expected_sources,
        expected_tool=expected_tool,
        answer_has_citation=answer_has_citation,
        source_hit=source_hit,
        permission_correct=permission_correct,
        tool_call_correct=tool_call_correct,
        refusal_correct=refusal_correct,
        called_tools=called_tools,
        checks=checks,
        passed=all(check.passed for check in checks),
    )


def aggregate_metrics(results: list[QuestionEvaluation]) -> dict[str, Any]:
    return {
        "questions": len(results),
        "retrieval_hit_rate": _rate(
            result.source_hit for result in results if result.source_hit is not None
        ),
        "answer_has_citation_rate": _rate(
            result.answer_has_citation
            for result in results
            if result.expected_behavior == "answer"
        ),
        "permission_accuracy": _rate(
            result.permission_correct
            for result in results
            if result.permission_correct is not None
        ),
        "tool_call_accuracy": _rate(
            result.tool_call_correct
            for result in results
            if result.tool_call_correct is not None
        ),
        "refusal_accuracy": _rate(
            result.refusal_correct
            for result in results
            if result.refusal_correct is not None
        ),
        "question_pass_rate": _rate(result.passed for result in results),
    }


def _build_checks(
    question: EvalQuestion,
    response: RAGResponse,
    source_hit: bool | None,
    answer_has_citation: bool,
    tool_call_correct: bool | None,
    permission_correct: bool | None,
    refusal_correct: bool | None,
) -> list[EvaluationCheck]:
    checks: list[EvaluationCheck] = []
    if question.expected_sources:
        checks.append(
            EvaluationCheck(
                name="expected_source",
                passed=bool(source_hit),
                details=f"expected one of {question.expected_sources}",
            )
        )

    if question.expected_behavior == "answer":
        checks.append(
            EvaluationCheck(
                name="citation_present",
                passed=answer_has_citation,
                details="answer questions should include at least one citation",
            )
        )

    if question.expected_tool:
        checks.append(
            EvaluationCheck(
                name="expected_tool",
                passed=bool(tool_call_correct),
                details=f"expected tool {question.expected_tool}",
            )
        )

    if question.expected_behavior == "deny_permission":
        checks.append(
            EvaluationCheck(
                name="permission_denied",
                passed=bool(permission_correct),
                details="restricted question should refuse without expected restricted source",
            )
        )

    if question.expected_behavior in {"deny_permission", "fallback"}:
        checks.append(
            EvaluationCheck(
                name="refusal",
                passed=bool(refusal_correct),
                details="question should produce a refusal or fallback answer",
            )
        )

    for expected_text in question.expected_answer_contains:
        checks.append(
            EvaluationCheck(
                name="answer_contains",
                passed=_contains_text(response.answer, expected_text),
                details=f"expected answer to contain: {expected_text}",
            )
        )

    for forbidden_text in question.forbidden_answer_contains:
        checks.append(
            EvaluationCheck(
                name="answer_does_not_contain",
                passed=not _contains_text(response.answer, forbidden_text),
                details=f"expected answer not to contain: {forbidden_text}",
            )
        )

    return checks


def _source_hit(expected_sources: list[str], response: RAGResponse) -> bool:
    citation_text = " ".join(
        " ".join(
            value or ""
            for value in (
                citation.title,
                citation.url,
                citation.source,
                citation.chunk_id,
            )
        )
        for citation in response.citations
    )
    normalized_citations = _normalize(citation_text)
    return any(_normalize(source) in normalized_citations for source in expected_sources)


def _normalize(value: str) -> str:
    normalized = value.lower().replace(".md", "")
    for character in ("_", "-", "/", "."):
        normalized = normalized.replace(character, " ")
    return " ".join(normalized.split())


def _is_refusal_like(answer: str) -> bool:
    normalized = answer.lower()
    refusal_markers = (
        "do not have enough",
        "not enough permitted",
        "using a role with access",
        "ask me a question about the indexed knowledge base",
    )
    return any(marker in normalized for marker in refusal_markers)


def _contains_text(answer: str, expected_text: str) -> bool:
    return _normalize(expected_text) in _normalize(answer)


def _rate(values: Any) -> dict[str, int | float | None]:
    collected = [bool(value) for value in values]
    total = len(collected)
    passed = sum(1 for value in collected if value)
    score = round(passed / total, 3) if total else None
    return {"passed": passed, "total": total, "score": score}
