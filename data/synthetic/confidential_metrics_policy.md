---
title: Confidential Metrics Policy
source: synthetic_internal
category: governance
permission_level: admin
updated_at: 2026-05-01
synthetic: true
---

# Confidential Metrics Policy

Confidential business metrics are restricted to admin users in this demo. They must not be
retrieved for guest, developer, or data analyst roles. The assistant should refuse requests
for restricted metrics when the user's role does not permit access.

Restricted examples include customer-level revenue metrics, contractual performance
penalties, private account identifiers, and non-public partner reporting.
