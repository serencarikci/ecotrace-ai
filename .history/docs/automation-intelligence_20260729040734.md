# Intelligent Automation, Forecasting, Anomaly Detection, and Production Hardening

**Status:** Complete (v0.7.3)  
**Scope:** Automation and intelligence capabilities for production use.

## Summary

This area extends the modular monolith with safe agents, automation rules, scheduled jobs, anomaly detection, forecasting, data quality monitoring, alerts/notifications, scheduled reports, supplier monitoring, regulatory intelligence, observability hooks, backup tooling, and production hardening — without weakening earlier platform foundations.

## Modules

- `agents` — allowlisted tools, executions, human approvals
- `automation` — organization rules, templates, idempotent runs
- `job_execution` — job records, locking, retries, scheduler worker
- `anomaly_detection` — deterministic detectors (z-score, IQR, % change, missing data)
- `forecasting` — linear / MA / WMA / seasonal naive / SES; target trajectory labels
- `data_quality` — scans and issues
- `alerts` / `notifications` — org-scoped alerts; in-app notifications (+ logging email provider)
- `scheduled_reports` — schedules and generated artifacts with checksums
- `supplier_monitoring` — internal non-certified assessments
- `regulatory_intelligence` — demo documents + human-reviewed applicability
- `production_operations` — shared ORM models for automation and intelligence

## Safety model

- LLM providers never access the database directly.
- Agent tools call application services only.
- Write tools create `agent_action_requests`; execution requires separate approval.
- Destructive agent/automation actions are forbidden.
- Cross-organization access is rejected by RBAC helpers.

## Scheduler

Docker Compose service `scheduler` runs `python -m ecotrace.scheduler_main`.  
Jobs persist in PostgreSQL. Concurrent duplicates are prevented via execution keys and worker locks. Misfire policy: advance to next run (documented). Scheduler captures due automations as job markers; interactive/manual runs execute with a user identity via API.

## Migration

- Alembic revision: `0007_intelligence`

## Known limitations

- PDF report output is a minimal portable stub, not full typography rendering.
- Email uses a development logging provider unless SMTP is configured.
- No Kafka/Celery; DB-polled scheduler.
- Regulatory seed content is **demo only** — not legal advice.
- Supplier scores are **internal / non-certified**.
- Forecasts are deterministic estimates, not probabilistic guarantees.
- PITR is an infrastructure option, not implemented by application scripts.

See also: [automation](automation.md), [agent-security](agent-security.md), [anomaly-detection](anomaly-detection.md), [forecasting](forecasting.md), [regulatory-intelligence](regulatory-intelligence.md), [production-readiness](production-readiness.md), [final-system-overview](final-system-overview.md).
