# Product Requirements Specification (MVP)

Project: AI Product Feedback Synthesis Assistant

Version: MVP

Date: 2026-07-29

Author: Product Manager / Software Architect

---

## Table of Contents

1. User Personas
2. User Stories
3. Acceptance Criteria
4. MVP Scope
5. Functional Requirements
   - Dashboard
   - CSV Upload
   - AI Analysis
   - Theme Review
   - Reports
6. Non-Functional Requirements
   - Performance
   - Security
   - Reliability
   - Maintainability
   - Accessibility
   - Scalability
7. Risks and Assumptions
8. Success Criteria

---

## 1. User Personas

### Product Manager
- Primary responsibilities: prioritize product work, convert user insights into roadmap items, and communicate findings to stakeholders.
- Goals: fast, defensible synthesis of user feedback with evidence-backed problem statements and easy export for stakeholders.
- Tech comfort: moderate; expects clear UIs and downloadable artifacts.

### Product Analyst
- Primary responsibilities: ingest, clean, cluster, and synthesize customer feedback; prepare reports and track trends.
- Goals: accurate grouping, deterministic counts and distributions, ability to curate AI-suggested themes, and maintain auditability.
- Tech comfort: high; expects data exports, filtering, and tools to manipulate themes (rename, split, merge).

### Administrator
- Primary responsibilities: manage organization settings, feature flags (AI on/off), user roles, and historical themes; ensure security and compliance.
- Goals: configure system defaults, manage access, and inspect audit logs.
- Tech comfort: high; expects an admin panel and RBAC controls.

---

## 2. User Stories

Note: All stories use the format: As a <role>, I want <goal>, so that <benefit>.

1. As a Product Analyst, I want to upload a CSV with defined fields, so that I can ingest raw feedback for synthesis.
2. As a Product Analyst, I want the system to validate the CSV schema and show parsing errors, so that I can correct input before processing.
3. As a Product Analyst, I want deterministic analytics (counts by theme, distribution by source/user type, time series) computed from the raw data, so that reported metrics are reproducible and auditable.
4. As a Product Analyst, I want the AI to propose suggested themes (clusters) and a suggested problem statement for each theme, so that I can accelerate synthesis.
5. As a Product Analyst, I want to see supporting feedback items (citations) for each suggested theme, so that I can verify the evidence behind a theme.
6. As a Product Analyst, I want to rename a theme, so that labels match organizational language.
7. As a Product Analyst, I want to merge multiple themes into one, so that I can consolidate related themes.
8. As a Product Analyst, I want to split a theme by moving selected feedback items into a new theme, so that I can correct over-aggregated clusters.
9. As a Product Analyst, I want to reject a suggested theme, so that noise is excluded from reports while preserving audit history.
10. As a Product Manager, I want to approve selected themes, so that approved themes become part of a saved synthesis report for stakeholders.
11. As a Product Manager, I want to export a reviewed synthesis report (JSON/CSV/PDF) that includes deterministic metrics and citations, so that I can share it with stakeholders and keep an auditable record.
12. As an Administrator, I want to upload or manage a small set of historical themes/product notes, so that the AI can compare new themes to historical ones.
13. As an Administrator, I want to enable/disable AI suggestion features via a feature flag, so that I can control LLM usage for privacy or cost concerns.
14. As an Administrator, I want role-based access control (Admin, Analyst, Reviewer, Viewer), so that only authorized users perform sensitive actions.
15. As a Product Analyst, I want an immutable audit log recording all theme operations and approvals (user, timestamp, before/after), so that changes are traceable and reversible.
16. As a Product Analyst, I want progress and status indicators (parsing, AI job, ready) and clear loading/empty/error states, so that I understand system state while working.
17. As a Product Analyst, I want the ability to view the original CSV snapshot and row-level detail, so that I can inspect raw inputs referenced by themes.
18. As a Product Analyst, I want to search and filter feedback items and themes, so that I can quickly locate evidence or problem areas.

---

## 3. Acceptance Criteria

Acceptance criteria are grouped and referenced by the user story number.

1. CSV Upload (Story 1)
   - Given I am authenticated as an Analyst, when I upload a CSV file containing the required columns (feedback text, source, user type, product area, date, optional rating), then the server accepts the file and returns an ingest job id and a preview of the first 10 rows.
   - The original CSV is stored as an immutable snapshot and associated with the ingest job id.

2. CSV Validation (Story 2)
   - Given an uploaded CSV, the system validates column headers and basic row-level types (date parseable, required fields non-empty). If validation fails, the system returns a list of row/column errors with row numbers and descriptive messages.
   - The UI displays validation errors and blocks AI analysis until the ingest errors are resolved or the analyst chooses to continue with warnings.

3. Deterministic Analytics (Story 3)
   - Given an ingested CSV, deterministic analytics computations (total items, distribution by source, distribution by user type, and time-series counts) complete and are accessible via API.
   - The counts must be computed by server-side code; any AI-provided numeric summaries are labeled as suggestions and must match the deterministic results to display as authoritative.

4. AI Suggested Themes (Story 4)
   - Given an ingested CSV and AI feature enabled, an AI job can be queued; when complete, the system shows suggested themes with a suggested label, suggested problem statement, suggested supporting snippets, and a confidence score.
   - The UI marks these as AI suggestions and does not mark them Approved automatically.

5. Supporting Feedback (Story 5)
   - For each suggested theme, the UI displays the list of underlying feedback items (showing original CSV row id, text, source, user type, date). The number of displayed items equals the deterministic membership count for the theme.

6. Rename Theme (Story 6)
   - When an analyst renames a theme, the new name is persisted, the audit log records the change with previous name and user/timestamp, and all subsequent exports show the updated name.

7. Merge Themes (Story 7)
   - When multiple themes are merged, a new theme is created (or one chosen as the target) and deterministic counts and distributions are recomputed to include all member items; the audit log records the merge with prior theme ids and user/timestamp.

8. Split Theme (Story 8)
   - When an analyst selects a subset of feedback items to split from a theme, a new theme is created containing those items, counts and distributions are recomputed for both themes, and the audit log records the split with item ids and user/timestamp.

9. Reject Theme (Story 9)
   - Rejecting a theme marks it as Rejected (excluded from active lists and exports but retained in DB); the audit log records the reject action and reason; the UI allows toggling to view rejected themes.

10. Approve Themes (Story 10)
    - Approving a theme marks it Approved and prevents further AI-only auto-approval; an approved flag and approving user/timestamp is saved; approved themes are included in saved synthesis reports.

11. Export Report (Story 11)
    - Exported report includes: list of approved themes, deterministic counts and distributions per theme, time-series data, all supporting citations (CSV row ids and raw texts), AI suggestion texts (labeled), and audit log excerpt. All numeric values match server-side deterministic computations.
    - The export can be downloaded as JSON and CSV. PDF export optional for MVP but must include core fields if implemented.

12. Historical Themes (Story 12)
    - Admin can upload a small set of historical themes (JSON/CSV) or product notes. When present, the AI analysis job returns suggested matches and similarity scores for new themes.

13. Feature Flag (Story 13)
    - Admin can disable AI suggestion jobs at the project level; when disabled, no LLM calls are made and the UI hides AI suggestion controls.

14. RBAC (Story 14)
    - Admin can create/manage users and assign roles. Server-side enforcement prevents unauthorized actions (e.g., only Analysts/Admins can approve themes).

15. Audit Log (Story 15)
    - All CRUD operations on themes and reports generate immutable audit records: operation type, user id, timestamp, change details. Records are queryable via the UI.

16. Progress & States (Story 16)
    - System shows clear statuses for ingest jobs (Queued, Parsing, Ready, Failed) and AI jobs (Queued, Running, Completed, Failed). UI displays loading/empty/error states consistently.

17. View Original CSV (Story 17)
    - Analyst can open the original CSV snapshot and see row-level detail including row id, full text, and original field values.

18. Search & Filter (Story 18)
    - Analysts can search feedback text and filter by source, user type, and product area; filters apply to both raw items and theme membership views.

---

## 4. MVP Scope

Included in MVP
- CSV upload with server-side validation and immutable snapshot storage.
- Deterministic analytics: counts by theme (after mapping), distributions by source and user type, and time-series aggregation.
- AI-suggested theme extraction and problem-statement drafting (feature-flagged); AI outputs are suggestions only and stored with logs.
- Theme management UI and APIs: rename, merge, split, reject, approve.
- Audit log for theme operations and approvals.
- Export reviewed synthesis report (JSON, CSV). PDF optional.
- Basic RBAC (Admin, Analyst, Viewer) and admin controls for AI feature flag and historical themes upload.
- Structured logs and minimal tests for CSV parsing and analytics.
- Public deployment for review (hosted link) and documented README, AGENT_USAGE.md, and .env.example.

Excluded from MVP
- Automated AI-driven prioritization or roadmap recommendations (explicitly excluded).
- Advanced plagiarism/fraud detection beyond basic duplicate detection and embedding similarity hints.
- Full ATS integrations, calendar scheduling, or multi-organization tenanting.
- Rich PDF layout or advanced templating engines for exports (basic export is included).
- Production-grade ML model retraining, bias auditing dashboards, or complex analytics pipelines (left for post-MVP).
- Offline/desktop clients and multi-language (non-English) support.

---

## 5. Functional Requirements

This section details functional behavior by feature area and ties back to user stories and acceptance criteria.

### Dashboard
- Description: Central landing page showing upload status, recent ingests, and quick actions to start analysis.
- Requirements:
  - Show recent ingest jobs with status (Queued, Parsing, Ready, Failed) and timestamp.
  - Show quick link to "Upload CSV", "View Recent Reports", and toggle for AI feature flag (for Admins).
  - Show a summary widget of last processed dataset: item count, suggested theme count (if AI enabled), number approved, number rejected.
  - Provide search bar to locate ingests, themes, or feedback items.

### CSV Upload
- Description: Accept and validate CSVs with the defined schema.
- Requirements:
  - Accept CSV files via frontend upload or API, require the following columns: feedback text, source, user type, product area, date, optional rating.
  - Validate headers, row-level types (date parseable), and required fields non-empty; return clear error messages with row numbers.
  - Store immutable snapshot of the original CSV in object storage and persist ingest metadata in DB.
  - Provide preview of first 10 rows and an ingest job id.
  - Support chunked parsing for large files and show progress.

### AI Analysis
- Description: Background jobs that produce suggested themes and problem statements.
- Requirements:
  - Orchestrate AI jobs via a background queue and worker; feature-flaggable by Admin.
  - Produce suggested clusters (themes) with: suggested label, suggested problem statement, confidence score, and list of supporting snippets (row ids and excerpts).
  - Persist AI inputs/outputs, model metadata, timestamps, and error logs for audit (do not store secrets in repo).
  - Provide endpoint and UI to display AI suggestions and link them to deterministic analytics outputs.
  - Allow Admin to upload historical themes for comparison. When present, AI should provide similarity scores and links to matched historical entries.

### Theme Review
- Description: UI and APIs for curating AI-suggested themes and creating final approved themes.
- Requirements:
  - View list of suggested and existing themes, showing name, status (Suggested, Approved, Rejected), member count, and deterministic distributions.
  - Theme Detail page: list of member feedback items (with pagination), deterministic metrics, AI suggestion text, and audit history for the theme.
  - Actions: Rename, Merge, Split, Reject, Approve.
  - Merge: select 2+ themes to combine; system recomputes counts and updates audit log.
  - Split: select subset of items from a theme to create a new theme; system recomputes counts and updates audit log.
  - Reject: mark theme as rejected; exclude from active lists and exports but retain in DB and audit.
  - Approve: mark theme approved and include in exports; requires user confirmation.
  - All actions are captured in immutable audit log entries.

### Reports
- Description: Save and export reviewed synthesis reports for stakeholders.
- Requirements:
  - Save a synthesis report that includes: metadata (dataset id, uploaded by, timestamp), list of approved themes, deterministic counts/distributions/time series per theme, supporting citations (CSV row ids and raw texts), AI suggestion texts (labeled), and audit excerpt.
  - Export formats: JSON and CSV required; PDF optional.
  - Ability to re-open saved report for further edits (version history kept in audit log).

---

## 6. Non-Functional Requirements

### Performance
- CSV parsing and validation: ingest and preview for files up to 10k rows should complete within 30 seconds on typical dev/prod hardware. Background AI jobs may be asynchronous and show progress.
- UI responsiveness: primary views (dashboard, theme list, theme detail) should load within 300ms for cached requests and within 1 second for cold DB queries under nominal load.

### Security
- Transport encryption (TLS) for all network traffic.
- RBAC enforced server-side for all actions; JWT or session-based auth with CSRF protections for forms.
- No secrets in repo; provide .env.example. Store credentials in CI/CD secret store for deployments.
- Input sanitization on all uploaded files and text fields to prevent injection.
- Redact PII before any external LLM call by default (configurable by Admin). Log what is sent to LLM and preserve only non-sensitive outputs when required.

### Reliability
- Background jobs use a queue with retry policy and a dead-letter queue for failures.
- Deterministic analytics produce identical results for the same input (idempotent operations).
- Export and critical write operations are ACID: theme modifications and approval actions should be transactional.

### Maintainability
- Clear separation of deterministic analytics logic from AI orchestration logic.
- Unit tests for CSV parsing, analytics, and theme operations; integration tests for end-to-end upload -> AI suggestion -> approve -> export flow.
- Documented AGENT_USAGE.md describing prompts and verification steps.

### Accessibility
- Candidate aim: basic WCAG 2.1 AA compliance: semantic HTML, ARIA labels for interactive controls, keyboard navigation for primary flows.

### Scalability
- MVP to support single-organization usage and files up to 10k rows. Design should permit horizontal scaling of web servers and workers; vector store and DB chosen with scale paths in mind.

---

## 7. Risks and Assumptions

### Risks
- LLM latency or quota limits could slow AI suggestion availability. Mitigation: feature-flag AI, provide cached or synthetic suggestions, and show clear progress states.
- LLM may hallucinate or invent numeric summaries. Mitigation: deterministic counts computed server-side and labeled authoritative; AI outputs always labeled as "Suggested".
- Data privacy when using external LLM providers. Mitigation: redact PII by default; Admin can disable AI or require self-hosted models.
- Time constraints (48-hour deadline) mean some UX flows will be minimal; mitigate by prioritizing core flows and documenting omissions.
- Merge/split operations could produce incorrect membership if concurrency is not handled. Mitigation: perform merges/splits transactionally and lock affected themes until operation completes.

### Assumptions
- Input CSVs follow a reasonably consistent schema; minimal cleansing needed for MVP.
- The evaluation environment allows secure usage of an LLM provider or local model within project constraints.
- Single-organization scope for MVP (no multi-tenant isolation required).
- Analysts will perform final approval — AI outputs are advisory only.

---

## 8. Success Criteria

- Core functional success:
  - CSV upload and deterministic analytics work end-to-end on sample datasets (<=10k rows).
  - AI suggestions produce plausible suggested themes and problem statements when AI feature is enabled.
  - Analysts can perform rename/merge/split/reject/approve operations and save/export a reviewed report.
  - Audit log contains a record for every theme operation and approval.

- Quality and reliability:
  - Deterministic counts reported in UI and exports match raw CSV contents without discrepancy.
  - System is stable during demo with no critical errors and clear error handling for recoverable issues.

- Delivery and documentation:
  - README.md explains setup, architecture, and deployed URL.
  - AGENT_USAGE.md documents LLM usage, representative prompts, and any agent mistakes.
  - .env.example lists required configuration keys.

- Usability:
  - A Product Analyst can complete an end-to-end synthesis (upload → review AI suggestions → approve → export) within 20 minutes on average for a 1k-row CSV.

---

End of document.
