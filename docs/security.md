# Security Architecture (MVP)

Project: AI Product Feedback Synthesis Assistant

Date: 2026-07-29

Author: Senior Security Architect

Purpose
This document outlines the security architecture and controls for the MVP. It covers input validation, file upload security, SQL injection prevention, XSS prevention, CORS policy, API key protection, secrets management, rate limiting, error handling, logging of sensitive data, and secure deployment considerations.

Scope
Applies to frontend (React), backend (FastAPI), storage (S3-compatible), and deployment environments (Render, Vercel). The goal is to provide pragmatic, production-grade security controls suitable for a first production release.

---

1. Input Validation

Principles
- Validate all inputs server-side as the source of truth. Client-side validation is UX enhancement only.
- Use strict schemas for all endpoints (Pydantic models for FastAPI). Reject requests that do not conform.

Controls
- Use Pydantic for request parsing/validation; set constrains (min_length, max_length, regex) on fields.
- Reject unexpected additional fields by configuring models to forbid extra fields.
- Normalize and sanitize string inputs (trim, normalize unicode) before use.
- Date validation: accept ISO-8601 formats only; reject other formats.
- For CSV ingestion: validate headers and types and return a detailed error report; do not attempt to auto-correct serious schema violations.

Defense-in-depth
- For file content, validate content-type and sniff the file contents to ensure it is valid CSV and not disguised executable content.

---

2. File Upload Security

Risks
- Uploaded files may contain malware, large payloads, or be used for storage flooding.

Controls
- Reject disallowed file types; only accept `text/csv` or validated textual content.
- Limit file size: enforce server-side maximum (e.g., 50MB for MVP) and return 413 on exceed.
- Use chunked upload for large files but require server-side reassembly and validation.
- Scan uploaded files for malware if possible (e.g., ClamAV) for higher-risk environments.
- Store uploaded files in object storage (S3/compat) with private access (not public). Only store and serve via signed URLs with expiry for downloads.
- Sanitize filenames and never use user-supplied filenames directly in storage paths.
- Store only metadata in DB; do not read file into memory fully for large files — stream processing recommended.

Preservation and retention
- Implement retention policy for raw CSV snapshots and provide deletion APIs for GDPR compliance.

---

3. SQL Injection Prevention

Principles
- Use parameterized queries/ORM rather than string interpolation.

Controls
- Use SQLAlchemy ORM / core with bound parameters for all DB operations.
- Never concatenate user-provided strings into SQL; if raw SQL needed, use safe binding.
- Use database roles with least privilege for DB users — separate readonly and write roles if necessary.
- Validate and sanitize identifiers (table/field names) if used to build queries dynamically.

Testing
- Include SQL injection tests in CI (fuzzing typical attack payloads) to ensure detection.

---

4. XSS Prevention

Principles
- Treat all user-provided content as untrusted. Escape-on-output.

Controls
- Frontend: escape any text displayed in DOM where HTML might be injected; prefer textContent over innerHTML.
- When allowing rich text (not in MVP), sanitize on backend using well-maintained sanitizer (DOMPurify on client, blech on server) and store sanitized HTML.
- For any dynamic HTML content in reports or emails, sanitize before rendering.

Content Security Policy (CSP)
- Deploy a strict CSP header: default-src 'self'; script-src 'self' 'unsafe-inline' only during dev; style-src 'self' 'unsafe-inline' minimized; connect-src to allowed APIs and resources. Relax per needs but prefer strict policy.

---

5. CORS Policy

Principles
- Restrict cross-origin access to known origins.

Controls
- Configure backend CORS to accept only allowed origins (Vercel frontend domain, local dev origins) and required methods.
- Do not use wildcard (*) in production.
- Set appropriate Access-Control-Allow-Credentials if cookies are used for auth.

---

6. API Key Protection

Principles
- Protect API keys and limit their scope and lifetime.

Controls
- Store API keys and provider credentials in server-side environment variables or managed secret store. Never send keys to client.
- When calling webhooks or receiving webhooks, sign payloads with HMAC and validate signature in backend.
- Rotate third-party keys regularly and document rotation procedure.

Credentials for AI and storage
- If using external LLM providers, store provider keys securely, log usage without exposing full key values, and use per-application or per-org tokens if available.

---

7. Secrets Management

Principles
- Centralize secrets, avoid plaintext in repo or logs.

Controls
- Use Render secrets and Vercel environment variables for production.
- For local dev, use .env files excluded from VCS; provide .env.example.
- Use HashiCorp Vault or cloud KMS for advanced setups.
- Grant least privilege to services and rotate credentials periodically.

---

8. Rate Limiting

Purpose
- Protect backend from abusive requests and control LLM costs.

Controls
- Implement rate limiting on critical endpoints using per-user and per-org quotas: e.g., /api/v1/ai_jobs limited to N calls per minute per org.
- Implement global rate limits per IP for public endpoints.
- Use 429 status code when limits exceeded and include Retry-After header.
- Track per-user token usage for AI calls and surface usage metrics to Admins.

---

9. Error Message Strategy

Principles
- Provide helpful developer-facing details in logs; keep user-facing messages concise and non-sensitive.

Controls
- Return structured error payloads: { code, message, details? }
- Do not return stack traces or internal exception details to clients.
- For validation errors include field-level details but avoid exposing raw DB errors.
- Use consistent error codes and map them to HTTP statuses.

Examples
- 400 Bad Request for malformed inputs
- 401 Unauthorized for missing/invalid token
- 403 Forbidden for insufficient permission
- 422 Unprocessable Entity for semantic validation (CSV row errors)

---

10. Logging Sensitive Data

Principles
- Avoid logging PII or secrets. When necessary, redact sensitive values.

Controls
- Use structured logging with fields for correlation id, user id (or hashed id), but never log raw secrets or full PII.
- For LLM prompts and outputs, store content in protected storage with access controls; redact PII before persistence unless explicitly required and authorized.
- Mask sensitive substrings in logs replacing with [REDACTED_EMAIL], [REDACTED_TOKEN].

Audit logs
- Store audit logs with action, actor, timestamp, and a minimal description. Audit logs may include references to feedback row ids but avoid including raw PII.

---

11. Secure Deployment Considerations

Network & infrastructure
- Use managed Postgres (TLS enabled), private network where possible, and restrict DB access to backend services only.
- Run backend in private network or isolated service with egress controls; only allow necessary outbound connections (LLM provider endpoints, S3).
- Use TLS for all external communications. Terminate TLS at Render/Vercel or at an external load balancer.

Access control
- Use least-privilege IAM for cloud resources. Limit access to secrets stores and production logs.
- Use multi-factor authentication (MFA) for admin console access (Render, Vercel, DB).

CI/CD
- Protect production branches; require PR reviews and successful CI checks before deployment.
- Store CI secrets in GitHub Actions secrets or provider secret stores; rotate periodically.

Backups & recovery
- Schedule regular DB backups and test restore procedures.
- Use object storage lifecycle and versioning for CSV snapshots; retain based on privacy policy.

Monitoring & alerts
- Monitor for abnormal patterns: high AI job rates, failed auth attempts, large file uploads, error spikes.
- Integrate with incident notification (PagerDuty or Slack).

Compliance & data protection
- Implement data deletion endpoints and retention policies for GDPR/CCPA compliance. Log deletion events in audit logs.

---

Appendix: Checklist for release
- Validate environment variables are set in Render/Vercel secrets (no plaintext in repo)
- Ensure CORS configured to allowed frontend origins
- Confirm rate limits and quotas configured and tested
- Confirm LLM keys stored securely and access is limited
- Confirm logs are structured and PII redaction in place
- Confirm backups configured and restore tested

End of Security Architecture document.
