# Agentic Knowledge Assistant

A local RAG demo for cloud platform operations. It ingests Markdown into PostgreSQL with
PGVector, filters retrieved chunks by role, and uses a LangGraph workflow to answer from
documents or call a mock metrics API and a read-only SQL tool.

The corpus combines summaries of [public MWS documentation](data/raw/public_mws) with
[fictional internal documents](data/synthetic). This project is not affiliated with MTS or
MWS. It contains no private company documents or live internal integrations.

## Run locally

Requires Docker and Docker Compose. The default embeddings are deterministic; an API key
is optional.

```bash
cp .env.example .env
make up
```

In another terminal, initialize the database and ingest both document sets:

```bash
make init-db
make ingest
curl http://localhost:8000/health
```

The health endpoint returns `{"service":"ok","database":"ok"}` when both services
are ready.

## Ask a question

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"demo_user","role":"developer","message":"How do I configure Kafka ingestion?"}'
```

The response has `answer`, `sources`, `tool_calls`, and `trace_id` fields. Other examples:

- Metrics: ask as `data_analyst`, “What was p95 latency for kafka_ingestion in the last 24 hours?”
- SQL: ask as `data_analyst`, “Show failed rows in pipeline_runs for kafka ingestion.”
- Access filter: ask as `guest` about the internal Kafka ingestion runbook; restricted chunks
  must not appear in the answer or sources.

Run `make demo-walkthrough` to print requests for all four cases, or
`python scripts/demo_walkthrough.py --execute` to call the local API.

## How it works

- Ingestion parses frontmatter, cleans and chunks Markdown, hashes documents to skip
  unchanged content, embeds chunks, and stores them in PostgreSQL with PGVector.
- Retrieval applies `permission_level` filters before passing chunks to the answer node.
  Roles are `guest`, `developer`, `data_analyst`, and `admin`.
- The agent classifies a question and routes it to retrieval, the mock metrics API, or
  read-only SQL over the demo `pipeline_runs` table.
- Without `OPENAI_API_KEY`, embeddings are deterministic and answers are extractive.
  Set the key and embedding settings in `.env` to use an OpenAI-compatible embedding API.

Role filtering is a demo metadata policy, not authentication or production IAM. Metrics,
pipeline rows, and internal documents are synthetic.

## Checks and evaluation

```bash
make test-local
make test-docker
make eval
```

`make test-local` checks Python compilation, line length, and Git whitespace.
`make test-docker` runs the unit tests in the API container. `make eval` compares baseline
retrieval with the agent workflow on the controlled questions in
[`data/eval/questions.yaml`](data/eval/questions.yaml). The dataset checks source hits,
citations, permissions, tool calls, and refusals; it is a regression check, not a
production benchmark. Run `make audit` for Bandit and dependency checks.

The current limits are rule-based intent classification, deterministic default embeddings,
extractive answers, a narrow SQL tool, and a small synthetic evaluation set.
