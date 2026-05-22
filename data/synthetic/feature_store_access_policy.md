---
title: Feature Store Access Policy
source: synthetic_internal
category: ml_platform
permission_level: analytics
updated_at: 2026-05-01
synthetic: true
---

# Feature Store Access Policy

The feature store provides curated features for analytics and model training. Feature
tables must include an owner, freshness expectation, entity key, training-serving parity
notes, and allowed consumer roles.

Access rules:

- public feature documentation may be read by any role
- developer users may read integration guides but not restricted feature values
- data analyst users may read approved analytics feature tables
- admin users may review restricted operational feature metadata

New feature access requests must include the business purpose, dataset name, consumer
application, retention need, and expected query volume.
