# Testing Strategy

Project: AI Product Feedback Synthesis Assistant (MVP)

Date: 2026-07-29

Author: Senior QA Engineer

Purpose
This testing strategy documents the approach for verifying correctness, robustness, security, and performance of the MVP. It covers unit, integration, API, frontend, CSV validation, AI workflow, edge cases, performance testing, and a manual testing checklist. The goal is to provide comprehensive testing guidance to ensure reliable delivery.

Testing tools & frameworks (recommended)
- Backend: pytest, pytest-cov, httpx for API tests, factory_boy for test data
- Frontend: Jest, React Testing Library, Cypress for end-to-end
- CI: Run tests in GitHub Actions
- Load/perf: k6 or Locust
- Security scanning: Bandit (Python), npm audit, Snyk (optional)

---

1. Unit Testing

Scope
- Test pure functions and business logic in isolation: CSV parsing helpers, deterministic analytics computations, clustering helpers, and small utility functions.

Approach
- Mock external dependencies (DB, LLM, embedding provider, object storage).
- Use pytest with fixtures and parametrized tests for typical and boundary inputs.
- Keep tests fast (<100ms per unit test ideally).

Coverage
- Aim for >80% unit test coverage for backend logic; focus on critical modules: CSV parser, analytics, theme operations.

Examples
- CSV parser: valid rows, missing columns, malformed dates, large number of columns
- Deterministic analytics: distribution calculations, time-series bucketing
- Theme membership operations: add/remove member, merge/split recomputation

---

2. Integration Testing

Scope
- Verify interactions between components: API endpoints with DB, workers running embedding jobs with DB persistence, and end-to-end flows: upload -> parse -> AI suggestion (mocked) -> review -> export.

Approach
- Use a test Postgres instance (Docker) with alembic migrations applied in test setup.
- Use ephemeral object storage (minio or local filesystem) for CSV snapshots.
- Mock LLM/embedding provider network calls but test orchestration logic.
- Use pytest fixtures for DB session and app client (FastAPI TestClient or httpx AsyncClient).

Key scenarios
- Full ingest flow with valid CSV: upload -> parsing -> ingest ready -> preview
- Theme CRUD operations: create, rename, merge, split, approve, reject
- Report generation and export

---

3. API Testing

Scope
- Validate REST API contract, validation behavior, authentication, and authorization.

Approach
- Use httpx to call endpoints in integration tests.
- Test both positive and negative paths including malformed payloads and RBAC enforcement.

Test cases
- Auth: login/refresh/me
- Ingest endpoints: create ingest (multipart), get ingest detail, preview rows
- AI jobs: create job (with feature flag on/off), job polling, suggestions retrieval
- Themes: list, detail, rename/merge/split/approve/reject
- Reports: save, list, export

Validation
- Ensure proper HTTP status codes, error payload shapes, and that numeric deterministic metrics match DB computed values.

---

4. Frontend Testing

Scope
- Component unit tests, integration tests for page flows, and end-to-end tests simulating a user.

Approach
- Unit: Jest + React Testing Library for components (presentation, forms, small interactions)
- Integration: render pages with mocked API responses using MSW (Mock Service Worker)
- E2E: Cypress to run core flows against deployed review environment or local dev setup (upload, review, approve, export)

Test cases
- CSV Upload page: file chooser, validation error displays, preview table
- Theme Review: selecting theme, approving, merge/split modals
- Reports: saving and downloading

Accessibility
- Include automated axe checks in CI for key pages.

---

5. CSV Validation Testing

Scope
- Verify CSV parsing and validation logic thoroughly with edge cases.

Approach
- Create a suite of CSV fixtures (valid, invalid headers, missing required fields, malformed dates, large rows, extra columns, BOMs, different line endings)
- Tests: server returns accurate error list with row numbers; preview shows first N rows correctly; snapshot stored

Validation cases
- Missing required columns
- Extra unexpected columns
- Non-parseable dates
- Empty feedback_text
- Files larger than max size -> 413
- Unicode and encoding issues (UTF-8 BOM, Latin-1) ensure graceful error or normalization

---

6. AI Workflow Testing

Scope
- Verify orchestration, embedding batching, clustering behaviors, LLM prompt handling, and output validation.

Approach
- Mock embedding provider responses and LLM outputs in unit and integration tests to test downstream logic.
- Include tests that send malformed LLM output to the parsing/validation step to ensure retry and rejection behavior.

Test cases
- Embedding batch processing: correct vectorization per item and storing
- Clustering deterministic behavior: given mocked embeddings, clustering yields expected clusters
- LLM output validation: accept well-formed JSON, reject malformed and trigger reformat retry
- Evidence mapping validation: ensure LLM-cited feedback_item_ids exist and excerpts match raw text; invalid citations are rejected

Cost & rate-limit handling
- Simulate LLM rate-limit errors and ensure retry/backoff and DLQ behaviors are exercised

---

7. Edge Cases

List of critical edge cases to test
- Concurrent operations on themes: two parallel merges/splits causing conflicts
- Large CSV (10k rows): performance and memory usage; chunked parsing behavior
- Completely empty CSV or CSV with only headers
- Duplicate feedback items: identical text or dup row numbers
- Rapid repeated AI job submissions exceeding rate limit
- Permission escalation attempts: viewer trying to approve themes
- Files with embedded control characters or very long lines

Approach
- Write unit/integration tests to simulate concurrency (db transactions and locks) and assert consistency

---

8. Performance Testing

Scope
- Ensure backend can handle expected loads: typical ingest sizes (1k–10k rows), concurrent users, and AI job throughput.

Approach
- Use k6 or Locust for load testing
- Run performance tests in staging environment mirroring production resources

Key metrics
- Ingest parsing throughput: rows/sec and total time for 1k, 5k, 10k rows
- API latency under load (p95, p99)
- Worker throughput for embedding and clustering (items/min)
- Memory/CPU usage for workers and API servers

Scenarios
- Simulate multiple concurrent ingests (5–10) while users access theme review
- Simulate queue with workers scaled to N and measure processing backlog

Acceptance criteria
- P95 response times within acceptable bounds (per PRS: < 1s for primary pages)
- No OOM or server crashes under expected peak load

---

9. Manual Testing Checklist

Pre-release manual checks
- [ ] Upload a sample CSV and verify ingest preview, parsing, and deterministic analytics
- [ ] Run AI analysis on sample dataset and verify suggestions show and citation links open correct raw rows
- [ ] Rename a theme and confirm audit log entry
- [ ] Merge two themes and verify member counts and audit entries
- [ ] Split a theme and verify both themes have correct counts
- [ ] Approve a theme and save/export a report; verify export includes deterministic metrics and citations
- [ ] Verify RBAC: Analyst can approve; Viewer cannot approve
- [ ] Verify CSV validation error reporting with malformed CSV
- [ ] Test UI for empty/loading/error states and accessibility keyboard navigation
- [ ] Test retention/deletion: delete ingest and confirm child records cascade or archive per policy
- [ ] Test AI failure scenarios: provider error, malformed output handling, and DLQ behavior

Security manual checks
- [ ] Confirm CORS is restricted to allowed origins
- [ ] Confirm secrets not present in repo and environment variables are used
- [ ] Test rate limiting and 429 behavior for AI job endpoints

Operational checks
- [ ] Verify logs are visible in central logging and include request_id
- [ ] Verify alerts trigger for AKS or Render incidents

---

10. Test Data & Fixtures

- Provide sanitized test CSVs covering positive and negative cases in tests/fixtures/csv/
- Provide factory functions for users, ingests, feedback items, themes for ease of test setup
- Provide sample AI outputs for mocking in tests/fixtures/ai/

---

11. CI Integration

- Run unit tests, linter, type-checking in CI on PRs
- Run integration tests in CI on main branch with a small test DB or per-PR test environment
- Run frontend tests (Jest) and E2E (Cypress) as part of release pipelines or nightly

---

12. Test Reporting

- Store coverage reports and test artifacts in CI runs and attach to PRs
- Fail build if coverage drops below defined threshold

---

13. Release Validation

Before publishing a release build to production
- Execute smoke tests in staging verifying key flows (upload->parse->AI->approve->export)
- Run DB migration in staging and test for breakages
- Verify monitor dashboards and alerting

---

End of Testing Strategy.
