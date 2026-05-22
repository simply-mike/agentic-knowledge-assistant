---
title: Incident Response Playbook
source: synthetic_internal
category: operations
permission_level: developer
updated_at: 2026-05-01
synthetic: true
---

# Incident Response Playbook

Platform incidents are classified by user impact, data freshness risk, and recovery time.
The first responder should create an incident record, assign an owner, capture the current
symptoms, and preserve logs before restarting services.

Initial response checklist:

- confirm whether the issue affects ingestion, processing, storage, or serving
- identify the newest successful pipeline run
- check recent deployments and configuration changes
- publish a status update with impact, workaround, and next update time
- avoid destructive recovery actions until the owner approves them

After mitigation, the owner writes a short review with timeline, root cause, user impact,
follow-up actions, and detection gaps.
