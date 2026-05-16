import re
from dataclasses import dataclass

from app.agents.state import Intent


@dataclass(frozen=True)
class IntentCandidate:
    intent: Intent
    score: int
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class IntentClassification:
    intent: Intent
    confidence: float
    candidates: list[IntentCandidate]
    reason: str


INTENT_PATTERNS: dict[Intent, tuple[str, ...]] = {
    "docs_question": (
        "how",
        "what",
        "explain",
        "configure",
        "setup",
        "guide",
        "runbook",
        "documentation",
        "object storage",
        "kafka",
        "spark",
        "lakehouse",
    ),
    "metrics_question": (
        "metric",
        "metrics",
        "latency",
        "p95",
        "success rate",
        "failed jobs",
        "records processed",
    ),
    "sql_question": (
        "select",
        "sql",
        "table",
        "pipeline_runs",
        "query the database",
    ),
    "access_request": (
        "access",
        "permission",
        "permissions",
        "role",
        "policy",
        "iam",
        "bucket policy",
    ),
    "general_chat": (
        "hello",
        "hi",
        "what are you",
        "who are you",
    ),
}

WEAK_DOCS_TERMS = {"how", "what", "explain"}
EXPLICIT_DOCS_TERMS = {
    "configure",
    "setup",
    "guide",
    "runbook",
    "documentation",
}
EXPLICIT_METRICS_TERMS = {
    "metric",
    "metrics",
    "latency",
    "p95",
    "success rate",
    "failed jobs",
    "records processed",
}

INTENT_PRIORITY: dict[Intent, int] = {
    "docs_question": 50,
    "metrics_question": 40,
    "sql_question": 30,
    "access_request": 20,
    "general_chat": 10,
    "unknown": 0,
}


def classify_query_intent(query: str) -> IntentClassification:
    normalized_query = _normalize(query)
    if len(normalized_query) < 3:
        return IntentClassification(
            intent="unknown",
            confidence=0.0,
            candidates=[],
            reason="query is too short",
        )

    candidates = sorted(
        _score_intents(normalized_query),
        key=lambda candidate: (candidate.score, INTENT_PRIORITY[candidate.intent]),
        reverse=True,
    )
    if not candidates:
        return IntentClassification(
            intent="docs_question",
            confidence=0.35,
            candidates=[],
            reason="defaulted to docs_question because no specialized intent matched",
        )

    primary = _choose_primary_intent(candidates)
    confidence = _confidence(primary, candidates)
    reason = _classification_reason(primary, candidates)
    return IntentClassification(
        intent=primary.intent,
        confidence=confidence,
        candidates=candidates,
        reason=reason,
    )


def _score_intents(normalized_query: str) -> list[IntentCandidate]:
    candidates: list[IntentCandidate] = []
    for intent, patterns in INTENT_PATTERNS.items():
        matched_terms = tuple(
            pattern for pattern in patterns if _matches(pattern, normalized_query)
        )
        if matched_terms:
            candidates.append(
                IntentCandidate(
                    intent=intent,
                    score=len(matched_terms),
                    matched_terms=matched_terms,
                )
            )
    return candidates


def _choose_primary_intent(candidates: list[IntentCandidate]) -> IntentCandidate:
    intents = {candidate.intent for candidate in candidates}
    sql_candidate = next(
        (candidate for candidate in candidates if candidate.intent == "sql_question"),
        None,
    )
    if sql_candidate and _has_explicit_sql_signal(sql_candidate):
        return sql_candidate

    metrics_candidate = next(
        (candidate for candidate in candidates if candidate.intent == "metrics_question"),
        None,
    )
    docs_candidate = next(
        (candidate for candidate in candidates if candidate.intent == "docs_question"),
        None,
    )
    if (
        metrics_candidate
        and _has_explicit_metrics_signal(metrics_candidate)
        and not (docs_candidate and _has_explicit_docs_signal(docs_candidate))
    ):
        return metrics_candidate

    if docs_candidate and len(intents) > 1 and _has_strong_docs_signal(docs_candidate):
        return docs_candidate
    return candidates[0]


def _confidence(primary: IntentCandidate, candidates: list[IntentCandidate]) -> float:
    total_score = sum(candidate.score for candidate in candidates)
    if total_score == 0:
        return 0.0
    return round(primary.score / total_score, 3)


def _classification_reason(
    primary: IntentCandidate,
    candidates: list[IntentCandidate],
) -> str:
    matched = ", ".join(primary.matched_terms)
    if len(candidates) == 1:
        return f"matched {primary.intent} terms: {matched}"

    other_intents = ", ".join(candidate.intent for candidate in candidates if candidate != primary)
    return (
        f"matched {primary.intent} terms: {matched}; "
        f"also detected secondary intents: {other_intents}"
    )


def _has_strong_docs_signal(candidate: IntentCandidate) -> bool:
    return any(term not in WEAK_DOCS_TERMS for term in candidate.matched_terms)


def _has_explicit_sql_signal(candidate: IntentCandidate) -> bool:
    return any(
        term in {"select", "sql", "table", "pipeline_runs", "query the database"}
        for term in candidate.matched_terms
    )


def _has_explicit_metrics_signal(candidate: IntentCandidate) -> bool:
    return any(term in EXPLICIT_METRICS_TERMS for term in candidate.matched_terms)


def _has_explicit_docs_signal(candidate: IntentCandidate) -> bool:
    return any(term in EXPLICIT_DOCS_TERMS for term in candidate.matched_terms)


def _matches(pattern: str, normalized_query: str) -> bool:
    if " " in pattern:
        return pattern in normalized_query
    return bool(re.search(rf"\b{re.escape(pattern)}\b", normalized_query))


def _normalize(query: str) -> str:
    return " ".join(query.lower().split())
