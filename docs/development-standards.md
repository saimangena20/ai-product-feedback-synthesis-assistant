# Development Standards

Project: AI Product Feedback Synthesis Assistant (MVP)

Date: 2026-07-29

Purpose
This development standards document defines consistent, team-wide conventions and best practices to ensure readable, maintainable, and high-quality code across the full stack (frontend and backend). It covers coding styles, naming, repository practices, logging, error handling, API design, database naming, documentation, and git workflows.

Scope
Applies to all engineers working on the repository: frontend (React + TypeScript + Tailwind), backend (FastAPI + Python + SQLAlchemy + Alembic), database (PostgreSQL), tests (pytest), and deployment (Render, Vercel).

---

1. Coding Standards

General principles
- Readability over cleverness. Prefer clear, explicit code.
- Single Responsibility: functions and classes should do one thing.
- DRY but not at cost of clarity: avoid duplication when abstraction improves clarity.
- Small functions and small modules. Aim for files < 400 lines.
- Use type annotations throughout (Python typing and TypeScript types/interfaces).
- Write unit tests for business logic and integration tests for important flows.
- Add docstrings and inline comments for non-obvious logic.

Formatting and tooling
- Frontend:
  - Prettier for formatting
  - ESLint with recommended TypeScript + React rules
- Backend:
  - black for formatting
  - isort for import sorting
  - flake8 for linting (optional) with team rules
- CI: Run linters and formatters in CI and fail builds on lint errors.

Code review
- All commits to main must go through PRs with at least one approving review.
- PRs should be small and scoped; provide an explanatory description and link to related docs/tickets.
- Include unit/integration test results in PRs.

---

2. Python Style Guide

Base
- Follow PEP8 and PEP257 docstring conventions.
- Use black (line length 88) and isort.
- Use type hints for all public functions and methods.

Project structure
- One package `app` containing application code.
- `app/api`, `app/core`, `app/db`, `app/models`, `app/schemas`, `app/crud`, `app/services`, `app/tests`.

Docstrings and typing
- Use Google-style or NumPy-style docstrings consistently (choose one and document in repo; recommend Google-style).
- Public functions: include parameter and return types in docstrings if not obvious from annotations.

Exceptions
- Define custom exception classes in app/core/exceptions.py for domain-specific errors.
- Use built-in exceptions for low-level issues.

Dependency injection and config
- Use FastAPI Dependencies for request-scoped resources (DB session, auth).
- Use pydantic BaseSettings for configuration (app/core/config.py).

Testing
- Use pytest with fixtures for DB and client setup.
- Tests should be deterministic and isolated; avoid external network calls in unit tests (mock providers).

---

3. React Style Guide

Component design
- Prefer functional components with hooks.
- Keep components small and focused; separate container (data fetching) and presentational components.
- Name components with PascalCase.
- Use PropTypes in JS or TypeScript interfaces for props; prefer TypeScript.

State management
- Use local state (useState, useReducer) for component-level state.
- Use context sparingly for cross-cutting concerns (auth, theme). For more complex global state consider lightweight solutions (zustand) only if necessary.

Side effects
- Use useEffect for side-effects and always define cleanup.
- Prefer async/await with try/catch and graceful error handling.

Styling
- Tailwind CSS for utility-first styling; keep className lists readable via clsx library.
- Avoid inline styles except for dynamic calculated values.

Accessibility
- Follow ARIA guidelines and semantic HTML.
- Ensure keyboard navigation and screen-reader labels for interactive elements.

Testing
- Use React Testing Library for component tests and Jest for unit tests.
- Write tests for meaningful user interactions rather than implementation details.

---

4. TypeScript Style Guide

Compiler options
- Use strict mode: `"strict": true` in tsconfig.json.
- `noImplicitAny: true`, `strictNullChecks: true`, `esModuleInterop: true`.

Types and interfaces
- Prefer `interface` for object shapes; use `type` for unions and utility types.
- Avoid `any`. When unavoidable, document reason and scope usage.
- Use readonly where appropriate.

Generics
- Use generics to express reusable, type-safe abstractions.

Error handling types
- Use discriminated unions for operation results where helpful, e.g., `Result<T, E>` patterns.

Imports
- Prefer absolute imports with path aliases configured in tsconfig (e.g., `@/components`). Keep short import paths.

Testing
- Type-check tests as part of CI.

---

5. Naming Conventions

General
- Be descriptive and concise.
- Prefer nouns for classes/types and verbs for functions.

Frontend
- Components: PascalCase (ThemeCard.tsx)
- Hooks: useCamelCase starting with use (useFetchThemes.ts)
- Services: camelCase (apiClient.ts)
- CSS modules: kebab-case (theme-card.module.css)

Backend (Python)
- Modules/files: snake_case (theme_service.py)
- Classes: PascalCase (ThemeService)
- Functions: snake_case
- Constants: SCREAMING_SNAKE_CASE

Database
- Tables: plural snake_case (feedback_items, theme_memberships)
- Columns: snake_case

API endpoints
- Use nouns and kebab-case or lower-case with hyphens: `/api/v1/ingests`, `/api/v1/themes/{theme_id}/approve`
- Use HTTP verbs semantics correctly.

---

6. Folder Naming

- Use lower-case, hyphenated or snake_case folder names depending on language convention. For Python backend use snake_case. For frontend use camel or kebab-case for folders under src.
- Examples:
  - `app/services/ai/`
  - `src/components/ThemeCard/`

---

7. File Naming

- Frontend: React components as `ComponentName.tsx`; related CSS module `ComponentName.module.css`.
- Backend: `snake_case.py` modules; model classes in singular file or module grouping: `models/theme.py`.
- Tests: `test_<module>.py` or `<module>_test.py` depending on test conventions; prefer `test_*.py`.

---

8. Git Commit Convention

- Use Conventional Commits format for messages: `<type>(scope): subject`
- Types: feat, fix, docs, style, refactor, perf, test, chore
- Examples:
  - feat(api): add endpoint to create ingest
  - fix(ui): handle empty state for themes
- Body: brief description and motivation; include issue/PR references.

Commit granularity
- Keep commits focused and atomic. One logical change per commit.

---

9. Branch Naming Convention

- Use feature branches: `feature/<jira-id>-short-description` or `feat/short-description`
- Bugfixes: `fix/<jira-id>-short-description`
- Hotfixes: `hotfix/<issue>`
- Release branches: `release/v1.2.0`
- PRs target main and require CI to pass and approvals.

---

10. Environment Variable Standards

- Use `.env` locally, commit `.env.example` listing required variables without secrets.
- Prefix environment variables intended for frontend exposure with `NEXT_PUBLIC_` or similar and avoid leaking secrets.
- Centralize config in backend via Pydantic BaseSettings in `app/core/config.py`.
- Naming: use uppercase snake_case: `DATABASE_URL`, `REDIS_URL`, `S3_BUCKET`, `LLM_API_KEY`.
- Secrets: store in Render/Vercel secret stores in production.

---

11. Logging Standards

Goals
- Structured, machine-parsable logs for tracing and observability.

Backend
- Use JSON structured logs with fields: timestamp, level, service, module, request_id, user_id (if available), message, extra.
- Configure log levels per environment: debug in dev, info in staging, info/warn/error in prod.
- Include correlation/request id in all logs (generate at HTTP entry point and pass through context).

Frontend
- Console logs only in dev. Send client-side errors to a centralized error-tracking system (Sentry) with user anonymized context.

Sensitive data
- Avoid logging PII or secrets. If necessary, redact before logging.

---

12. Error Handling Standards

Principles
- Fail fast but recover gracefully where possible.
- Provide helpful error messages to clients with actionable remediation.

Backend
- Return structured error responses with `code`, `message`, and optional `details` for validation errors.
- Map exceptions to HTTP status codes: 400 for bad requests, 401/403 for auth/permission, 404 for not found, 422 for validation semantics, 500 for unexpected server errors.
- Use custom exception classes and middleware to convert exceptions to consistent error responses.

Frontend
- Show user-friendly messages; log technical details to error tracking for developers.
- Display validation errors inline next to fields.

---

13. API Design Standards

RESTful principles
- Use nouns for resources and HTTP methods for actions.
- Version API via path: `/api/v1/`.
- Use appropriate status codes and include useful response bodies.

Request/Response
- Use JSON for request/response with camelCase keys for frontend consumption. Pydantic models should set `alias_generator` if DB uses snake_case.
- Pagination: support `page` and `page_size` and return `X-Total-Count` header.
- Filtering & search: use query parameters (`?source=web&userType=beta`).

Security
- Require Bearer token for auth.
- Rate limit AI job endpoints and provide clear 429 responses.

Documentation
- Auto-generate OpenAPI docs via FastAPI and keep examples updated.

---

14. Database Naming Standards

- Tables: plural snake_case (e.g., feedback_items)
- Columns: snake_case
- Primary keys: id (uuid)
- Index names: idx_<table>_<column> (e.g., idx_feedback_items_ingest_id)
- Foreign keys: fk_<table>_<ref_table> (e.g., fk_feedback_items_ingest_id)
- Constraints: chk_<table>_<field> (e.g., chk_ingests_status)

Data types
- Use uuid for primary keys
- JSONB for flexible metadata and snapshots
- Use timestamp with time zone (timestamptz) for created_at

Migration
- Use Alembic for schema changes and adopt non-blocking migration patterns for large tables

---

15. Documentation Standards

- Keep docs/ folder authoritative for product, design, API, DB, and AI workflow artifacts.
- Update README.md with setup and run steps; keep .env.example in root.
- Inline code documentation: module-level docstrings and function docstrings for public APIs.
- ADRs (Architecture Decision Records): record major design decisions in docs/adr/.
- AGENT_USAGE.md: document all prompts and agent usage with examples and verification steps.

---

Appendix: Sample error response (standard)

HTTP 422
{
  "error": {
    "code": 422,
    "message": "CSV validation failed",
    "details": [ { "row": 12, "column": "feedback_text", "message": "Missing required field" } ]
  }
}

---

Enforcement
- Linting, formatting, and tests run in CI; PRs must pass all checks.
- Periodic code review audits and technical debt sprints to maintain standards.

End of document.
