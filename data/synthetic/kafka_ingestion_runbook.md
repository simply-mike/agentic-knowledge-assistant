---
title: Kafka Ingestion Runbook
source: synthetic_internal
category: data_platform
permission_level: developer
updated_at: 2026-05-01
synthetic: true
---

# Kafka Ingestion Runbook

Synthetic internal document for demonstration purposes. This document is not affiliated
with MTS or MWS and does not describe real internal systems.

Kafka ingestion jobs copy events from approved Kafka topics into the raw object-storage
zone. Each job must define a topic name, consumer group, target bucket path, schema
version, checkpoint location, and retry policy.

Configuration checklist:

- confirm that the topic is registered in the platform catalog
- use a stable consumer group name in the format `dp-{domain}-{dataset}`
- write raw events to `raw/{domain}/{dataset}/event_date=YYYY-MM-DD/`
- store checkpoints under `checkpoints/kafka/{domain}/{dataset}/`
- set `max_poll_records` according to event size and downstream latency
- enable dead-letter routing for malformed events

If lag increases, first check consumer group status, broker throttling, schema validation
errors, and object-storage write latency. Do not increase parallelism before confirming
that downstream storage can absorb the extra writes.
