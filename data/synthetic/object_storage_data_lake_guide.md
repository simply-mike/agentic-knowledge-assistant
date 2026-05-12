---
title: Object Storage Data Lake Guide
source: synthetic_internal
category: data_platform
permission_level: developer
updated_at: 2026-05-01
synthetic: true
---

# Object Storage Data Lake Guide

Synthetic internal document for demonstration purposes. This document is not affiliated
with MTS or MWS and does not describe real internal systems.

The demo data lake uses object storage zones to separate raw, cleaned, and curated data.
Raw data should preserve source events with minimal changes. Cleaned data should normalize
schemas and remove invalid records. Curated data should be optimized for analytics,
machine learning, and reporting.

Recommended layout:

- `raw/{domain}/{dataset}/event_date=YYYY-MM-DD/`
- `clean/{domain}/{dataset}/processing_date=YYYY-MM-DD/`
- `curated/{domain}/{dataset}/snapshot_date=YYYY-MM-DD/`

Datasets should define retention, owner, schema version, partition strategy, and quality
checks. Avoid storing credentials, access tokens, or personal secrets in object paths,
metadata files, or sample records.
