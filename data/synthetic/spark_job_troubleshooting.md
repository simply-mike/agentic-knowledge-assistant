---
title: Spark Job Troubleshooting
source: synthetic_internal
category: data_platform
permission_level: developer
updated_at: 2026-05-01
synthetic: true
---

# Spark Job Troubleshooting

Synthetic internal document for demonstration purposes. This document is not affiliated
with MTS or MWS and does not describe real internal systems.

Spark jobs process data from the raw and cleaned zones into curated tables. Common failure
classes are input schema drift, executor memory pressure, shuffle skew, missing partitions,
and slow object-storage reads.

Troubleshooting steps:

- check the job run status and the first failing stage
- compare input schema with the expected schema version
- inspect executor lost messages and out-of-memory errors
- review shuffle read size and skewed task duration
- verify that partition paths exist for the requested processing date
- rerun with a smaller date range if the failure is caused by one bad partition

For memory pressure, reduce input partition size, increase executor memory only after
reviewing shuffle behavior, and avoid collecting large datasets on the driver.
