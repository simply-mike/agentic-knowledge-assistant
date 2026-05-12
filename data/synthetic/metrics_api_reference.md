---
title: Metrics API Reference
source: synthetic_internal
category: observability
permission_level: analytics
updated_at: 2026-05-01
synthetic: true
---

# Metrics API Reference

Synthetic internal document for demonstration purposes. This document is not affiliated
with MTS or MWS and does not describe real internal systems.

The demo metrics API returns synthetic operational metrics for platform pipelines. It is
used by the assistant only as a mock internal tool in later phases.

Supported metric fields:

- `avg_latency_ms`
- `p95_latency_ms`
- `failed_jobs`
- `success_rate`
- `records_processed`

Supported periods are `last_1h`, `last_24h`, and `last_7d`. Pipeline names in the demo
include `kafka_ingestion`, `spark_curated_transform`, and `feature_publish`.

Metrics returned by this API are synthetic and must not be described as real production
measurements.
