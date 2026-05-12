---
title: Model Serving SLA
source: synthetic_internal
category: ml_platform
permission_level: developer
updated_at: 2026-05-01
synthetic: true
---

# Model Serving SLA

Synthetic internal document for demonstration purposes. This document is not affiliated
with MTS or MWS and does not describe real internal systems.

Model serving endpoints expose approved models for online inference. Each endpoint must
define an owner, model version, rollback version, expected request rate, latency target,
and alert routing.

Default service objectives:

- p95 inference latency below 250 ms for standard models
- availability target of 99.5 percent for production endpoints
- rollback completed within 15 minutes after a severe regression
- model version metadata included in each prediction log

When latency exceeds the target, inspect request volume, feature lookup latency, model
runtime duration, and downstream logging delays before changing compute size.
