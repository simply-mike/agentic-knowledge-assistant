---
title: Data Platform Overview
source: synthetic_internal
category: data_platform
permission_level: public
updated_at: 2026-05-01
synthetic: true
---

# Data Platform Overview

The demo data platform provides shared services for batch analytics, streaming ingestion,
feature preparation, model serving, and operational observability. Teams use it to move
data from application events into object storage, process data with Spark jobs, and expose
curated datasets to analytics and machine learning workflows.

The platform has four common layers:

- ingestion for Kafka topics, CDC exports, and scheduled file imports
- storage for raw, cleaned, and curated data zones in object storage
- processing for Spark transformations and validation jobs
- serving for feature store tables, dashboards, and model endpoints
