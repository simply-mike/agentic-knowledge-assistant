from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://localhost:8000"


@dataclass(frozen=True)
class DemoCase:
    name: str
    description: str
    role: str
    message: str
    expected: str
    filters: dict[str, Any] | None = None


DEMO_CASES = [
    DemoCase(
        name="docs",
        description="Grounded documentation answer with citations.",
        role="developer",
        message="How do I configure Kafka ingestion?",
        expected="Answer should cite the Kafka ingestion runbook.",
    ),
    DemoCase(
        name="metrics",
        description="Agent routes to the mock metrics API and retrieves related docs.",
        role="data_analyst",
        message="What was p95 latency for kafka_ingestion in the last 24 hours?",
        expected="Response should include a mock_metrics_api tool call.",
    ),
    DemoCase(
        name="sql",
        description="Agent uses the read-only SQL tool over the demo pipeline_runs table.",
        role="data_analyst",
        message="Show failed rows in pipeline_runs for kafka ingestion.",
        expected="Response should include a sql_tool call and table-shaped answer.",
    ),
    DemoCase(
        name="permission",
        description="Guest role cannot retrieve developer-only synthetic runbook content.",
        role="guest",
        message="What does the internal Kafka ingestion runbook say about retries?",
        filters={"source": "synthetic_internal", "permission_level": "developer"},
        expected="Response should refuse or fallback without leaking restricted sources.",
    ),
]


def main() -> None:
    args = parse_args()
    cases = select_cases(args.case)

    print_header(args.base_url)
    print_health_check(args.base_url)

    for demo_case in cases:
        print_case(args.base_url, demo_case)
        if args.execute:
            execute_case(args.base_url, demo_case, timeout_seconds=args.timeout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print or run the local API demo walkthrough.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="FastAPI service base URL.")
    parser.add_argument(
        "--case",
        choices=[demo_case.name for demo_case in DEMO_CASES],
        help="Run or print only one demo case.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually call the API. By default, only curl commands are printed.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds.")
    return parser.parse_args()


def select_cases(case_name: str | None) -> list[DemoCase]:
    if case_name is None:
        return DEMO_CASES
    return [demo_case for demo_case in DEMO_CASES if demo_case.name == case_name]


def print_header(base_url: str) -> None:
    print("Agentic Knowledge Assistant demo walkthrough")
    print("=" * 46)
    print(f"Base URL: {base_url.rstrip('/')}")
    print()
    print("Before executing calls, start the stack and ingest documents:")
    print()
    print("  cp .env.example .env")
    print("  make up")
    print("  make init-db")
    print("  make ingest")
    print()


def print_health_check(base_url: str) -> None:
    print("Health check")
    print("-" * 12)
    print(f"curl {base_url.rstrip('/')}/health")
    print()


def print_case(base_url: str, demo_case: DemoCase) -> None:
    payload = {
        "user_id": "demo_user",
        "role": demo_case.role,
        "message": demo_case.message,
    }
    if demo_case.filters:
        payload["filters"] = demo_case.filters

    print(f"{demo_case.name}: {demo_case.description}")
    print("-" * (len(demo_case.name) + len(demo_case.description) + 2))
    print(f"Expected: {demo_case.expected}")
    print("curl command:")
    print(
        "curl -X POST "
        f"{base_url.rstrip()}/chat "
        '-H "Content-Type: application/json" '
        f"-d '{json.dumps(payload)}'"
    )
    print()


def execute_case(base_url: str, demo_case: DemoCase, timeout_seconds: float) -> None:
    payload = {
        "user_id": "demo_user",
        "role": demo_case.role,
        "message": demo_case.message,
    }
    if demo_case.filters:
        payload["filters"] = demo_case.filters

    request = Request(
        f"{base_url.rstrip('/')}/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Execution failed for {demo_case.name}: {exc}")
        print()
        return

    print("Response summary:")
    print(f"  answer_preview: {response_payload.get('answer', '')[:180]}")
    print(f"  sources: {len(response_payload.get('sources', []))}")
    print(f"  tool_calls: {len(response_payload.get('tool_calls', []))}")
    print(f"  trace_id: {response_payload.get('trace_id')}")
    print()


if __name__ == "__main__":
    main()
