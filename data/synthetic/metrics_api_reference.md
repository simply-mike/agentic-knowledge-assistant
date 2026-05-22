---
title: Metrics API Reference
source: synthetic_internal
category: observability
permission_level: analytics
updated_at: 2026-05-01
synthetic: true
---

# Metrics API Reference

The demo metrics API returns synthetic operational metrics for platform pipelines.

Supported metric fields:

- `avg_latency_ms`
- `p95_latency_ms`
- `failed_jobs`
- `success_rate`
- `records_processed`

Supported periods are `last_1h`, `last_24h`, and `last_7d`. Pipeline names in the demo
include `kafka_ingestion`, `spark_curated_transform`, and `feature_publish`.
