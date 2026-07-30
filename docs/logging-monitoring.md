# Logging and Monitoring Strategy

Project: AI Product Feedback Synthesis Assistant (MVP)

Date: 2026-07-29

Author: Site Reliability Engineer

Purpose
This document defines the logging and monitoring strategy for the MVP. It covers application logs, API logs, AI logs, error logs, audit logs, log levels, rotation and retention, monitoring metrics, alerting and failure response. The goal is to ensure observability, rapid incident detection, root-cause analysis capability, and compliance with data protection requirements.

Principles
- Structured, machine-readable logs (JSON) with consistent fields.
- Correlation across services using request_id / trace_id for end-to-end troubleshooting.
- Separation of concerns: audit logs, AI model logs, and application logs have distinct handling and access controls.
- Privacy-first: redact or avoid logging PII and secrets; restrict access to sensitive logs.
- Metrics-driven monitoring: instrument key metrics and SLOs and attach alerts to meaningful thresholds.
- Small blast radius: implement rate limiting, queueing and graceful degradation; monitor and alert on critical backpressure signals.

---

1. Application Logs

Purpose
- Capture structured runtime logs for backend services and workers to diagnose behavior and trace flows.

Requirements
- Format: JSON structured logs with consistent schema.
- Transport: send logs to a centralized log collector (Logstash/Loki/Fluentd -> Elasticsearch/Grafana Loki / Cloud Logging).
- Sampling: no sampling for errors; for info-level high-volume events, optional low-rate sampling (configurable).

Minimum log fields (each log entry)
- timestamp: ISO8601 (UTC)
- level: DEBUG|INFO|WARN|ERROR
- service: backend | worker | frontend | ai-worker
- environment: dev|staging|prod
- message: human-readable message
- request_id: uuid (if part of HTTP request path) — correlate across systems
- trace_id: trace id from OpenTelemetry (if tracing enabled)
- user_id: uuid|null (if authenticated) — consider hashing or pseudonymization
- org_id: uuid|null
- module: python module or component name
- function: optional
- error: structured error object (if applicable) {type, message, stacktrace?}
- extra: JSON object for any domain-specific fields (e.g., ingest_id, ai_job_id, theme_id)

Instrumentation
- At HTTP entry point generate request_id and include in response header X-Request-Id.
- Integrate OpenTelemetry for traces; attach trace_id to logs automatically.
- Use structured logger libraries (python: structlog or logging with JSON formatter; frontend: send structured events to monitoring).

Access controls
- Production logs are restricted; role-based access control for viewing logs (admins, SRE, limited PMs).

Retention and rotation
- Retain production application logs for 90 days in hot storage; archive for 1 year in cold storage depending on compliance. Shorter retention for dev/staging.

---

2. API Logs

Purpose
- Provide request-level observability for API calls: latency, status code, request/response sizes, auth outcomes.

Logs & Metrics
- Log every inbound request at INFO level with fields: method, path, status_code, latency_ms, response_size_bytes, request_id, user_id (if present), org_id, client_ip (masked), user_agent (optional)
- For health-check endpoints, either sample or exclude from default dashboards to reduce noise.

Metrics to emit (Prometheus)
- api_http_requests_total{method,path,status_code}
- api_http_request_duration_seconds (histogram)
- api_http_request_size_bytes, api_http_response_size_bytes
- api_auth_failures_total

SLOs and targets
- 99th percentile latency for critical endpoints (e.g., ingest preview, theme list) < 1s
- Error rate (5xx) less than 1% of requests

---

3. AI Logs

Purpose
- Capture AI job lifecycle, provider interactions, prompts, responses (redacted), and cost/usage metadata for auditing and debugging.

Separation & Access
- AI logs contain sensitive content (prompts/outputs). Store them in a separate secure store with tighter access controls.
- Only authorized roles (SRE, Admin, designated reviewers) can access raw AI logs.

Minimum fields for AI job logs
- timestamp
- ai_job_id
- ingest_id
- requested_by (user_id)
- model_name, model_version
- prompt_hash (hash of prompt template + context)
- prompt_redacted (where PII removed) — store only if permitted
- response_redacted (highly recommended to store only redacted output or store in encrypted store)
- token_usage: {prompt_tokens, completion_tokens, total_tokens}
- latency_ms
- status: queued|running|completed|failed
- error: structured error if failed

Policy
- Redact PII from prompts before sending to provider and ensure redaction log shows what was removed (not original text) unless explicit consent exists.
- Record cost and token usage per job to enable billing alerts.

Retention
- Keep AI logs for 90 days in a high-access store, and optionally archive for audit for up to 1 year in cold storage; consult org privacy policy.

---

4. Error Logs

Purpose
- Capture full context for errors to enable root-cause analysis (RCA).

Guidelines
- Capture error-level logs with stack trace and structured context (request_id, user_id, ingest_id, ai_job_id, theme_id).
- Avoid logging raw PII in stack traces; sanitize before storing.
- For worker errors, include job metadata and last-known state transitions.

Alerts
- All ERROR logs emitted in prod should be counted; if error rate or number of ERROR logs spikes, generate alerts (see Failure Alerts section).

---

5. Audit Logs

Purpose
- Immutable recording of security- and compliance-sensitive events: theme approvals, merges, splits, user admin actions, data deletion, and consent changes.

Design
- Store audit logs in a separate append-only store/table (audit_logs) with strict RBAC and retention policy.
- Audit log fields:
  - timestamp
  - actor_id (user uuid)
  - actor_role
  - action (string, e.g., theme.approve)
  - resource_type and resource_id
  - before (jsonb) optional
  - after (jsonb) optional
  - metadata (reason, ip, client)
- Ensure immutability: do not allow regular updates; implement soft-delete only with policy-controlled process and record changes as new audit entries.

Access
- Restrict read access to auditors, Admins, and SRE; write access only via application service account.

Retention
- Retain audit logs per compliance requirements (commonly 1–7 years) depending on organization policy.

---

6. Log Levels

Definitions and usage
- DEBUG: verbose diagnostic information for development and troubleshooting. Not enabled in production except short windows.
- INFO: routine events (startup/shutdown, configuration changes, job start/stop, normal operations like ingest created).
- WARN: recoverable issues, degraded performance, retries, validation warnings.
- ERROR: failures that require attention; include stack trace and context.
- CRITICAL / FATAL: system-level failures requiring immediate attention and likely page.

Guidelines
- Log at INFO for normal state changes; use DEBUG for verbose details behind a feature flag or debug mode.
- Ensure logs can be filtered by level in the log system.

---

7. Log Rotation & Retention

Rotation
- Configure log shipping agent (Fluentd/Fluent Bit) to forward logs to central system and rotate local files daily.
- Keep local logs minimal and rely on central store for retention.

Retention policy
- Application logs (prod): 90 days hot; 1 year cold archive (configurable).
- AI logs: 90 days hot; archive 1 year if required.
- Audit logs: 1–7 years depending on compliance requirement; store in write-once cold storage if mandated.

Deletion & privacy
- Implement procedures for removing logs tied to data-subject requests (GDPR) — audit logs may need special handling and legal review before deletion.

---

8. Monitoring Metrics

Instrumentation
- Use Prometheus for metrics collection (instrument backend and workers) with Grafana dashboards.
- Instrument endpoints, queue sizes, job durations, LLM usage, DB metrics, system metrics (CPU, memory), and storage metrics.

Core metric categories
- API metrics
  - http_requests_total{method,path,status_code}
  - http_request_duration_seconds (histogram)
  - http_response_size_bytes
- Job & worker metrics
  - ai_jobs_submitted_total
  - ai_jobs_running_current
  - ai_jobs_failed_total
  - ai_job_duration_seconds (histogram)
  - embedding_batch_size
  - embedding_throughput_items_per_second
  - queue_length for job queues
- Database metrics
  - db_connections_current
  - db_query_duration_seconds (histogram for slow queries)
  - db_replication_lag_seconds
- Storage metrics
  - s3_put_errors_total
  - s3_get_errors_total
- Infrastructure metrics
  - cpu_usage_percent, memory_usage_bytes, disk_usage_bytes
- Cost & usage metrics
  - llm_token_usage_total by model
  - estimated_llm_cost_total

Dashboards (recommended)
- API Overview: request rates, top slow endpoints, error rates
- AI Jobs: job success/failure, token usage, average latency
- Worker/Queue: queue lengths, worker health
- Database: slow queries, connections
- Infra: CPU/memory/disk per service
- Cost dashboards: LLM token usage and estimated cost per day

SLOs & Targets (examples)
- Availability SLO: API availability 99.9% (exclude maintenance windows)
- Latency SLO: 95th percentile request latency < 500ms for theme list / preview endpoints
- Error SLO: 5xx rate < 1% over 5-minute window

---

9. Failure Alerts

Alert principles
- Alert on symptoms, not raw metrics; include context and suggested runbook steps.
- Avoid alert fatigue by setting reasonable thresholds and grouping related alerts.

Priority levels
- P1 (Pager): System outages, queue DLQ build-up, DB down, provider auth failures, LLM provider errors causing critical job failures
- P2 (Page or Slack): Elevated error rate, sustained high latency, job failure spikes, storage bucket errors
- P3 (Slack/Email): Resource usage nearing capacity, increasing error trend, minor infra issues

Key alert rules & suggested thresholds
- API 5xx spike: if 5xx rate > 1% of requests over 5 minutes -> P2
- Sustained high latency: p95 latency above 2s for 10 minutes -> P2
- AI job failure rate: if > 20% of AI jobs fail in 15 minutes -> P1/P2 depending on impact
- Queue depth: job queue length > 2x worker count for 15 minutes -> P2
- DLQ items > 0 -> P1 (requires immediate triage)
- LLM provider auth failure or 401 responses > 5 in 5 minutes -> P1
- DB connection errors/failed queries spike -> P1
- Disk usage > 80% -> P2; > 90% -> P1
- Backup failure -> P1

Alert content
- Include alert summary, affected services, recent logs (linked), related dashboards, and first-step runbook actions.

Escalation
- Use escalation policies (PagerDuty): P1 pages on-call SRE, P2 pages/Slack and on-call, P3 Slack/email to responsible team.

---

10. Tracing and Correlation

Tracing
- Use OpenTelemetry to instrument HTTP requests and background workers and export traces to Jaeger/Tempo.
- Correlate trace_id with logs and metrics via request_id and trace_id.

Correlation
- Ensure request_id is returned in API responses and included in all downstream job entries to allow cross-system lookup (logs, traces, job records).

---

11. Runbooks (brief)

Common incident: High AI job failure rate
1. Check AI jobs dashboard for failure patterns and recent errors.
2. Inspect AI logs (ai_job_id) for provider errors, auth issues, or malformed prompts.
3. Check LLM provider status and key rotation status.
4. If provider outage: pause new AI jobs (feature flag or rate limit), notify stakeholders, and consider fallback (defer jobs, use cached embeddings).
5. Clear DLQ only after understanding root cause; do not blindly retry.

Common incident: DLQ items present
1. Open DLQ list and inspect errors for each job.
2. For transient errors (network), schedule retries; for corruption or validation errors, notify product owner for manual cleanup.

Common incident: High error rate 5xx
1. Identify top endpoints by 5xx count and open logs filtered by request_id and error type.
2. Check recent deploys and config changes.
3. If error caused by DB outage, fail-safe degrade reads where possible and alert DB on-call.

---

12. Privacy and Compliance Notes

- PII: Avoid logging raw PII. If logs must reference user data, use pseudonymized user_id or hashed identifiers and store mapping separately with controlled access.
- Deletion: implement processes to identify and delete logs/data for data subject requests; audit deletions in audit_logs.
- Access controls: limit access to logs containing redacted content or AI outputs.

---

13. Implementation Checklist

- [ ] Implement structured JSON logging with standard schema across services
- [ ] Generate request_id at HTTP entry and include in responses
- [ ] Integrate OpenTelemetry traces and export to tracing backend
- [ ] Configure log forwarder to central log store and set retention policies
- [ ] Create Grafana dashboards for API, AI jobs, DB, and infra
- [ ] Define Prometheus metrics and instrument code
- [ ] Configure alerts in PagerDuty with escalation policies
- [ ] Setup RBAC for log and AI stores
- [ ] Document runbooks and attach to alerts

---

Appendix A: Sample log (JSON)

{
  "timestamp": "2026-07-29T15:00:00Z",
  "level": "ERROR",
  "service": "backend",
  "environment": "prod",
  "message": "Failed to process AI job",
  "request_id": "6f1a2b4c-...",
  "trace_id": "abcd-...",
  "user_id": "u-123",
  "org_id": "o-456",
  "module": "app.services.ai.runner",
  "ai_job_id": "job-789",
  "error": { "type": "ProviderError", "code": 429, "message": "Rate limited" },
  "extra": { "prompt_hash": "h-001", "token_usage": {"prompt":200, "completion":1200} }
}

---

End of Logging and Monitoring Strategy.
