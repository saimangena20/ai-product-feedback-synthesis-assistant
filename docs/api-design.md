# API Design — REST / OpenAPI-style

Project: AI Product Feedback Synthesis Assistant (MVP)

Date: 2026-07-29

This document provides a REST API specification in OpenAPI-style for the MVP. It covers authentication, ingest/upload, validation, deterministic analytics, AI orchestration, theme management, report generation, audit logs, and admin feature flags.

Authentication
- Mechanism: Bearer token (JWT) in Authorization header.
- All endpoints require authentication unless noted.
- Roles: admin, analyst, viewer. Server enforces RBAC for sensitive actions.

Common responses
- 200 OK — success with data
- 201 Created — resource created
- 202 Accepted — job queued/accepted for async processing
- 204 No Content — success with no body
- 400 Bad Request — validation error; response includes error details
- 401 Unauthorized — invalid or missing auth
- 403 Forbidden — insufficient permissions
- 404 Not Found — resource not found
- 409 Conflict — duplicate or conflicting resource
- 422 Unprocessable Entity — semantic validation failed (e.g., CSV row errors)
- 500 Internal Server Error — unexpected server error

Pagination
- List endpoints support `page` (1-based) and `page_size` query params, and return `X-Total-Count` header.

---

Schemas (reference)
- User:
  - id: uuid
  - email: string
  - display_name: string
  - role: enum(admin|analyst|viewer)
- Ingest:
  - id: uuid
  - org_id: uuid
  - uploaded_by: uuid
  - title: string
  - total_rows: integer
  - status: enum(queued|parsing|ready|failed)
  - created_at: timestamp
  - completed_at: timestamp|null
- CsvSnapshot:
  - id: uuid
  - ingest_id: uuid
  - storage_path: string
  - filename: string
  - file_size_bytes: integer
  - schema: json
  - created_at: timestamp
- FeedbackItem:
  - id: uuid
  - ingest_id: uuid
  - row_number: integer
  - feedback_text: string
  - source: string
  - user_type: string
  - product_area: string
  - feedback_date: date
  - rating: number|null
- Theme:
  - id: uuid
  - ingest_id: uuid
  - name: string
  - status: enum(suggested|approved|rejected|merged|archived)
  - ai_suggested_label: string|null
  - metrics_cache: json|null
  - created_by: uuid|null
  - created_at: timestamp
- AIJob:
  - id: uuid
  - ingest_id: uuid
  - requested_by: uuid
  - status: enum(queued|running|completed|failed|cancelled)
  - job_params: json
  - result_metadata: json|null
  - error: json|null
  - created_at: timestamp
  - completed_at: timestamp|null
- AISuggestion:
  - id: uuid
  - ai_job_id: uuid
  - suggested_label: string
  - suggested_problem_statement: string
  - confidence: number|null
  - model_metadata: json|null
- Report:
  - id: uuid
  - ingest_id: uuid
  - created_by: uuid
  - title: string
  - snapshot: json
  - include_audit: boolean
  - created_at: timestamp

---

1. Authentication

POST /api/v1/auth/login
- Description: Exchange credentials for JWT.
- Request body (application/json):
  - email: string
  - password: string
- Response 200:
  - { token: "<jwt>", user: {id,email,display_name,role} }
- Errors: 400, 401
- Notes: Support SSO via separate endpoints or OIDC flows in Admin scope.

POST /api/v1/auth/refresh
- Description: Refresh JWT using refresh token.
- Request body: { refresh_token }
- Response 200: { token, refresh_token }
- Errors: 401

GET /api/v1/auth/me
- Description: Return current user profile
- Auth: Bearer
- Response 200: User

---

2. Users & Organization

GET /api/v1/users
- Description: List users (Admin only)
- Query: page, page_size, role
- Auth: Admin
- Response 200: [User]
- Errors: 401,403

POST /api/v1/users
- Description: Create user (Admin)
- Auth: Admin
- Request body: { email, display_name, role }
- Response 201: User
- Validation: email required, role in allowed list
- Errors: 400,401,403,409

GET /api/v1/users/{user_id}
- Auth: Admin or self
- Response 200: User
- Errors: 401,403,404

PATCH /api/v1/users/{user_id}
- Description: Update user (Admin or self limited fields)
- Request body: { display_name?, role? }
- Auth: Admin or self
- Response 200: User
- Errors: 400,401,403,404

---

3. Feature Flags (Admin)

GET /api/v1/orgs/{org_id}/flags
- Auth: Admin
- Response: [{ key, enabled }]

PATCH /api/v1/orgs/{org_id}/flags/{key}
- Auth: Admin
- Request: { enabled: boolean }
- Response 200: { key, enabled }
- Errors: 400,401,403,404

---

4. Ingests & CSV Upload

POST /api/v1/ingests
- Description: Create ingest metadata and upload CSV
- Accepts: multipart/form-data
  - file: CSV file
  - title: string (optional)
  - description: string (optional)
- Auth: Analyst or Admin
- Response 202 Accepted:
  - { ingest_id, snapshot_id, job_id }
- Behavior:
  - Server stores CSV snapshot in object storage, creates ingest and csv_snapshot rows, enqueues parse/validation job and returns job id.
- Validation: file present, mime type text/csv
- Errors: 400,401,403,413 (file too large), 422 (invalid CSV)

GET /api/v1/ingests
- Description: List ingests
- Query: page, page_size, status, q
- Response 200: [Ingest]
- Headers: X-Total-Count
- Auth: Analyst/Admin/Viewer (scoped to org)

GET /api/v1/ingests/{ingest_id}
- Description: Get ingest detail including deterministic analytics summary
- Response 200: { ingest, snapshot, analytics: { total_items, distributions, time_series_summary } }
- Auth: org-scoped
- Errors: 401,403,404

DELETE /api/v1/ingests/{ingest_id}
- Description: Delete ingest (Admin only)
- Response 204
- Notes: deletes are cascade to child data per policy or require archival. May require extra confirmation param.
- Errors: 401,403,404

---

5. CSV Parsing/Validation Jobs

GET /api/v1/ingests/{ingest_id}/jobs/{job_id}
- Description: Get job status and validation results
- Response 200:
  - { job_id, type: 'parse', status: queued|running|completed|failed, errors: [{row, column, message, severity}], warnings: [...] }
- Errors: 401,403,404

POST /api/v1/ingests/{ingest_id}/jobs/{job_id}/retry
- Description: Retry parse job after fix
- Auth: Analyst/Admin
- Response 202
- Errors: 400,401,403,404

GET /api/v1/ingests/{ingest_id}/csv_snapshot
- Description: Get CSV snapshot metadata and download path
- Response 200: { snapshot_id, storage_path, filename, file_size_bytes }
- Auth: org-scoped

GET /api/v1/ingests/{ingest_id}/preview
- Description: Return first N rows preview
- Query: limit (default 10)
- Response 200: { rows: [ { row_number, fields... } ] }
- Auth: org-scoped

---

6. Feedback Items

GET /api/v1/ingests/{ingest_id}/items
- Description: List parsed feedback items (paginated)
- Query: page, page_size, q (search), source, user_type, product_area, date_from, date_to
- Response 200: [FeedbackItem]
- Auth: org-scoped

GET /api/v1/ingests/{ingest_id}/items/{item_id}
- Response 200: FeedbackItem with raw metadata
- Errors: 401,403,404

---

7. AI Jobs & Suggestions

POST /api/v1/ingests/{ingest_id}/ai_jobs
- Description: Trigger AI analysis job (feature-flagged)
- Auth: Analyst/Admin
- Request body (application/json):
  - requested_by (optional; server uses auth user)
  - job_params: { cluster_count?: integer, min_items_per_cluster?: integer }
- Response 202: { ai_job_id }
- Errors: 400,401,403,429 (rate limit), 503 (LLM provider unreachable)

GET /api/v1/ingests/{ingest_id}/ai_jobs/{ai_job_id}
- Response 200: { ai_job meta: status, created_at, completed_at, result_metadata, error }

GET /api/v1/ai_jobs/{ai_job_id}/suggestions
- Description: List suggestions produced for the job
- Response 200: [ { suggestion_id, suggested_label, suggested_problem_statement, confidence, model_metadata } ]

GET /api/v1/ai_suggestions/{suggestion_id}/snippets
- Response 200: [ { feedback_item_id, excerpt } ]

Errors: 401,403,404

Notes
- LLM prompt, inputs, and outputs must be stored in model_metadata or protected logs; consider redaction rules for PII before sending.

---

8. Themes & Theme Memberships

GET /api/v1/ingests/{ingest_id}/themes
- Description: List themes for ingest with filters
- Query: status (suggested|approved|rejected), q (search), page, page_size
- Response 200: [Theme] (each includes member_count and optional metrics_cache)

GET /api/v1/themes/{theme_id}
- Description: Theme detail with deterministic metrics and membership list (paginated)
- Response 200: { theme, metrics: { member_count, by_source, by_user_type, time_series }, members: [FeedbackItem] }

POST /api/v1/ingests/{ingest_id}/themes
- Description: Create a new theme (manual or from AI suggestion)
- Auth: Analyst/Admin
- Request body: { name, ai_suggested_label?, initial_member_item_ids?: [uuid] }
- Response 201: Theme
- Validation: name required, unique per ingest
- Errors: 400,401,403,409

PATCH /api/v1/themes/{theme_id}
- Description: Partial update (rename, note)
- Body: { name?, note? }
- Response 200: updated Theme
- Validation: name uniqueness
- Errors: 400,401,403,404,409

DELETE /api/v1/themes/{theme_id}
- Description: Mark theme as archived or delete (Admin)
- Response 204
- Errors: 401,403,404

POST /api/v1/themes/{theme_id}/members
- Description: Add feedback items to theme (bulk)
- Body: { item_ids: [uuid] }
- Response 200: { added: count }
- Errors: 400,401,403,404
- Notes: creates theme_memberships rows, recomputes metrics_cache

DELETE /api/v1/themes/{theme_id}/members
- Description: Remove items from theme
- Body: { item_ids: [uuid] }
- Response 200: { removed: count }
- Errors: 400,401,403,404

POST /api/v1/themes/merge
- Description: Merge multiple themes into target
- Auth: Analyst/Admin
- Request body: { source_theme_ids: [uuid], target_theme_id?: uuid, new_name?: string }
- Response 200: { target_theme_id, merged_count }
- Validation: at least 2 source ids, target exists or new_name provided
- Errors: 400,401,403,404,409,409
- Notes: Operation is transactional; audit log produced

POST /api/v1/themes/{theme_id}/split
- Description: Split selected member item ids into new theme
- Request body: { item_ids: [uuid], new_theme_name: string }
- Response 201: { new_theme_id }
- Validation: item_ids not empty, items belong to theme
- Errors: 400,401,403,404,409

POST /api/v1/themes/{theme_id}/approve
- Description: Approve a theme for inclusion in reports
- Auth: Analyst/Admin
- Body: { note?: string }
- Response 200: updated theme (status approved, approved_by, approved_at)
- Validation: theme must have >=1 member
- Errors: 400,401,403,404

POST /api/v1/themes/{theme_id}/reject
- Description: Reject a theme; reason required
- Body: { reason: string }
- Response 200: updated theme (status rejected)
- Validation: reason required (min length)
- Errors: 400,401,403,404

GET /api/v1/themes/{theme_id}/audit
- Description: Get audit history for theme
- Response 200: [AuditLog]

---

9. Reports

POST /api/v1/ingests/{ingest_id}/reports
- Description: Save a synthesis report snapshot
- Auth: Analyst/Admin
- Body: { title: string, description?: string, include_audit?: boolean, theme_ids: [uuid] }
- Response 201: { report_id }
- Validation: at least one theme_id and all theme_ids must be approved
- Errors: 400,401,403,404,409

GET /api/v1/reports
- Description: List reports (paginated, filter by ingest)
- Query: ingest_id, page, page_size
- Response 200: [ReportSummary]

GET /api/v1/reports/{report_id}
- Description: Get full report payload and download links
- Response 200: { report, report_themes: [theme_snapshot], downloads: { json, csv, pdf? } }
- Errors: 401,403,404

POST /api/v1/reports/{report_id}/export
- Description: Trigger export generation (JSON/CSV/PDF)
- Body: { formats: ['json','csv','pdf'], include_audit: boolean }
- Response 202: { export_job_id }
- Errors: 400,401,403,404

GET /api/v1/reports/{report_id}/exports/{export_id}
- Description: Check export job and download when ready
- Response 200: { status, download_url }
- Errors: 401,403,404

---

10. Audit Logs

GET /api/v1/audit
- Description: Query audit logs (Admin) with filters
- Query: resource_type, resource_id, actor_id, action, date_from, date_to, page, page_size
- Auth: Admin
- Response 200: [AuditLog]

---

11. Admin Endpoints

GET /api/v1/orgs/{org_id}/historical_themes
- Description: List historical themes uploaded for similarity matching
- Auth: Admin

POST /api/v1/orgs/{org_id}/historical_themes
- Description: Upload historical themes (JSON/CSV) used by AI for comparison
- Body: multipart/form-data { file }
- Response 201

---

12. Health & Diagnostics

GET /api/v1/health
- Public: returns 200 OK and basic service status summary (db: ok, queue: ok, storage: ok)

GET /api/v1/metrics
- Auth: Admin
- Response: basic operational metrics (ingest counts, ai job rates)

---

13. Webhooks (optional)
- POST /webhooks/ai_job_complete
  - Used if external workers notify the app of job completion. Secured with HMAC signature header.
  - Body: { ai_job_id, status, result_summary }
  - Response 200

---

Validation rules (general)
- All UUID parameters must be valid UUIDs; server returns 400 if malformed.
- Date parameters use ISO 8601 format (YYYY-MM-DD or full timestamp). Server returns 400 for invalid formats.
- CSV upload: maximum file size configurable, default 10MB for demo; server returns 413 for larger files.
- Name fields: max length 200 chars; trimmed; empty disallowed for required fields.
- Theme approval: requires at least one member; server returns 422 if not met.

Error payload example (400/422):
{
  "error": {
    "code": 422,
    "message": "CSV validation failed",
    "details": [ { "row": 12, "column": "feedback_text", "message": "Missing required field" } ]
  }
}

Security notes
- Redact PII before sending to external LLMs according to Admin policy.
- Log model prompts and outputs with access controls; consider retention policy for model logs.
- Rate-limit AI job creation per org and per user to avoid excessive costs.

---

Appendix: Example flows mapping to APIs
- Upload CSV: POST /api/v1/ingests -> returns ingest_id -> poll GET /api/v1/ingests/{ingest_id}/jobs/{job_id}
- Run AI: POST /api/v1/ingests/{ingest_id}/ai_jobs -> GET /api/v1/ai_jobs/{id} -> GET suggestions
- Approve theme: POST /api/v1/themes/{theme_id}/approve
- Save report: POST /api/v1/ingests/{ingest_id}/reports

---

End of API design document.
