# Project Structure and Conventions

Project: AI Product Feedback Synthesis Assistant (MVP)

Tech stack
- Frontend: React + TypeScript + Tailwind, deployed to Vercel
- Backend: FastAPI + SQLAlchemy + Alembic, deployed to Render
- Database: PostgreSQL
- Testing: Pytest (backend); frontend testing recommendations provided
- Deployment: Render (backend) & Vercel (frontend)

This document specifies a recommended, production-ready folder structure, file purposes, naming and coding conventions, import strategy, and configuration strategy. No implementation code is included here — this is a blueprint for engineering teams and for the assignment deliverable.

---

Root folder tree (complete)

/ (repo root)
├─ .github/
│  └─ workflows/
│     ├─ ci.yml
│     └─ deploy.yml
├─ apps/
│  ├─ frontend/                     # React + TypeScript + Tailwind app (Vercel)
│  │  ├─ public/
│  │  │  └─ favicon.ico
│  │  ├─ src/
│  │  │  ├─ components/
│  │  │  ├─ pages/
│  │  │  ├─ hooks/
│  │  │  ├─ services/
│  │  │  ├─ styles/
│  │  │  ├─ utils/
│  │  │  └─ app.tsx (or main.tsx)
│  │  ├─ package.json
│  │  ├─ tsconfig.json
│  │  ├─ tailwind.config.js
│  │  └─ .env.example
│  └─ backend/                      # FastAPI app (Render)
│     ├─ app/
│     │  ├─ api/
│     │  │  ├─ v1/
│     │  │  │  ├─ endpoints/
│     │  │  │  └─ deps.py
│     │  ├─ core/
│     │  │  ├─ config.py
│     │  │  └─ logging.py
│     │  ├─ db/
│     │  │  ├─ base.py
│     │  │  ├─ session.py
│     │  │  └─ migrations/ (alembic)
│     │  ├─ models/
│     │  ├─ schemas/
│     │  ├─ crud/
│     │  ├─ services/
│     │  │  ├─ ai/
│     │  │  └─ workers/
│     │  ├─ workers/
│     │  ├─ jobs/
│     │  ├─ tests/
│     │  └─ main.py
│     ├─ alembic.ini
│     ├─ pyproject.toml (or requirements.txt)
│     ├─ .env.example
│     └─ Dockerfile
├─ infra/
│  ├─ terraform/ (optional)
│  └─ render/ (render service definitions)
├─ scripts/
│  ├─ dev-run.sh
│  └─ migrate.sh
├─ docs/
│  ├─ product-requirements.md
│  ├─ ui-design.md
│  ├─ user-flow.md
│  ├─ database-design.md
│  └─ api-design.md
├─ tests/                            # Integration/system tests (Pytest)
│  ├─ integration/
│  └─ fixtures/
├─ .gitignore
├─ README.md
└─ .env.example


---

Folder & file purposes (important items)

/.github/
- Purpose: CI/CD pipeline definitions used by GitHub Actions. Define jobs for linting, tests, building artifacts, and optionally CD triggers. Files:
  - ci.yml: CI pipeline (run linters, unit tests, build front-end artifacts, run backend tests)
  - deploy.yml: optional deployment workflows to Vercel/Render using secrets

/apps/frontend/
- Purpose: Frontend application built with React + TypeScript + Tailwind; targets Vercel for deployment.
- Important files/folders:
  - public/: static assets served by the frontend (favicon, static images)
  - src/app.tsx or src/main.tsx: application entry
  - src/pages/: page-level components (if using Next.js) or routes (for SPA)
  - src/components/: reusable UI components (atoms, molecules)
  - src/hooks/: custom React hooks (prefixed with use)
  - src/services/: API clients and remote-service adapters (e.g., apiClient.ts)
  - src/styles/: Tailwind config files and global styles
  - src/utils/: pure utility functions
  - package.json: scripts and dependencies
  - tsconfig.json: TypeScript config
  - tailwind.config.js: Tailwind configuration
  - .env.example: env variables required at build/runtime

/apps/backend/
- Purpose: Backend service exposing REST API (FastAPI) and worker infrastructure for AI jobs.
- Important files/folders:
  - app/main.py: ASGI application entrypoint (create FastAPI app and include routers)
  - app/api/v1/endpoints/: route handlers grouped by domain (ingests, ai_jobs, themes, reports, auth)
  - app/api/v1/deps.py: dependency injection helpers (get_db, get_current_user)
  - app/core/config.py: centralized configuration using pydantic BaseSettings; reads from env
  - app/core/logging.py: structured log config
  - app/db/session.py: DB session creation and transaction helpers
  - app/db/base.py: base metadata for SQLAlchemy models and Alembic autogeneration
  - app/models/: SQLAlchemy model definitions (one module per logical model group)
  - app/schemas/: Pydantic schemas for request/response validation
  - app/crud/: data access layer functions (create_ingest, get_themes, etc.)
  - app/services/ai/: embedding/LLM orchestration helpers (wrap providers, redaction)
  - app/services/workers/: worker logic for background jobs (embedding batch, clustering)
  - app/workers/: specialized worker entrypoints (if using background worker process)
  - app/jobs/: job queue adapters (e.g., Redis, RQ, or Bull via fastapi-workers)
  - app/tests/: unit and integration tests that use pytest fixtures
  - alembic.ini and app/db/migrations/: Alembic configuration and versioned migrations
  - Dockerfile: container spec for Render or local dev
  - pyproject.toml / requirements.txt: backend dependencies and dev tools
  - .env.example: environment variables required at runtime

/infra/
- Purpose: Infrastructure as code for supporting resources (managed DB, object storage, vector DB). May be optional for MVP but recommended for production readiness.
- Files:
  - terraform/: Terraform modules to provision RDS (Postgres), S3-compatible bucket, Redis, and managed compute
  - render/: service definitions for Render (or manifests for other providers)

/scripts/
- Purpose: convenience scripts for local dev and maintenance (db migrations, seed data). Keep small wrapper scripts here and avoid environment-specific hardcoding.

/docs/
- Purpose: project documentation (this repo's planning artifacts, PRS, UI design, API design, DB design, user flows, AI workflow). All deliverables should live here.

/tests/
- Purpose: shared test assets, integration tests, and fixtures for faster CI runs. Use pytest with fixtures for DB setup/teardown.


---

Naming conventions

General principles
- Be consistent and predictable. Prefer explicit, descriptive names.
- Use language idioms: Python uses snake_case for modules and variables and PascalCase for classes; TypeScript React components use PascalCase for components and camelCase for functions/variables.

Frontend
- Files and folders: kebab-case for filenames and folders (e.g., src/components/theme-card/ThemeCard.tsx or src/components/theme-card/index.tsx). For components, prefer PascalCase filenames for React components (ThemeCard.tsx). Example: src/components/ThemeCard/ThemeCard.tsx
- Component names: PascalCase (ThemeCard)
- Hook names: prefixed with use (useFetchThemes.ts)
- Service files: camelCase (apiClient.ts)
- CSS classes: Tailwind utility classes; if component-scoped styles are used, file name theme-card.module.css

Backend (Python)
- Modules / files: snake_case (e.g., app/services/ai/embedding_service.py)
- Packages (folders): singular nouns (app/service, app/model)
- Classes: PascalCase (ThemeService)
- Functions and variables: snake_case
- Constants: SCREAMING_SNAKE_CASE
- Database models: singular PascalCase class name (Theme), table name set explicitly as plural snake_case ("themes")
- Alembic revision files: use automatic timestamps and short description: e.g., 20260729_add_themes_table.py

API & Database
- REST endpoints: kebab-case or lowercase with hyphens not required for APIs — prefer POSIX-style paths using nouns: /api/v1/ingests, /api/v1/themes, /api/v1/ai-jobs
- JSON keys: camelCase for frontend consumption (consistent with TypeScript models) — handle mapping in Pydantic models via alias generators if needed

Tests
- Test modules: test_*.py
- Test classes: Test* for grouping; prefer plain functions with fixtures rather than classes unless grouping needed
- Pytest fixtures: use descriptive names like ingest_fixture, db_session


---

Coding standards

Frontend (TypeScript/React)
- Use TypeScript strict mode ("strict": true in tsconfig)
- Functional components with hooks; prefer explicit prop types/interfaces
- Maintain separation: container (page-level) components handle data fetching; presentational components are pure
- Linting & formatting: ESLint + Prettier with shared rules; enforce in CI
- Accessibility: follow WCAG basics; all interactive elements keyboard-focusable with aria-labels

Backend (Python / FastAPI)
- Follow PEP8 and PEP257; use black for formatting and isort for imports
- Use pydantic for request/response validation and settings management
- Keep API routers thin and delegate business logic to services (app/services) and data access to app/crud
- Dependency injection via FastAPI dependencies for DB sessions and auth
- Use structured logging (JSON) with correlation ids (request id)
- Add type hints throughout and prefer small functions with single responsibility

Database & SQLAlchemy
- Use alembic migrations for schema changes; never modify production schema manually
- Use SQLAlchemy Core or ORM with clear sessions and scoped sessions in web context

Testing
- Unit tests for pure functions and small service layers
- Integration tests for API endpoints using test DB fixtures
- Aim for deterministic tests and avoid flakiness (no dependence on external LLM providers in CI)


---

Import strategy

Frontend
- Configure tsconfig paths for absolute imports from src (e.g., @/components, @/services). Example:
  - import ThemeCard from '@/components/ThemeCard'
- Prefer absolute imports to avoid long relative chains

Backend
- Package-mode imports using app as package root. e.g., from app.crud.theme import get_theme_by_id
- Use relative imports only within tightly-coupled modules
- Ensure tests run with PYTHONPATH set appropriately or install backend in editable mode in test environment (pip install -e .)


---

Configuration strategy

Environment variables
- Use .env for local development (excluded from repo; commit .env.example)
- Backend: app/core/config.py uses pydantic BaseSettings to centralize configuration with environment variable binding
- Frontend: use .env.development and Vercel environment variables (NEXT_PUBLIC_ prefixed for variables exposed to browser)

Secrets & credentials
- Never commit secrets. Use deployment provider secret store (Render environment variables and Vercel env vars) or Vault for production
- For local dev, developers use local credentials with clear .env.example listing required keys

Configuration files
- Common files: .env.example, README with setup steps
- CI: GitHub Actions use secrets; avoid printing secrets in logs

Feature flags
- Implement feature flags in DB (feature_flags table) and optionally in runtime configuration; Admin UI toggles values persisted to DB

Consistency
- Keep default values in code but allow runtime override via env variables and admin feature flags


---

Developer scripts and Makefile

- Provide simple scripts or Makefile targets for common tasks to unify developer experience:
  - make install              # install backend deps
  - make dev                 # start dev servers (frontend and backend)
  - make migrate             # apply alembic migrations
  - make test                # run pytest
  - make lint                # run linters
  - scripts/dev-run.sh       # helper to set env and run


---

CI/CD and deployment

- Frontend: Vercel automatic deploys on push to main (protect main with PRs)
- Backend: Render service with GitHub integration or GitHub Actions deploy step that builds Docker image and pushes to Render
- CI pipeline (.github/workflows/ci.yml): run linters, run unit tests (pytest), build frontend (type-check), and run integration tests (optionally with a test Postgres instance)
- Use semantic branch protection rules and PR reviews before merges to main


---

Observability & local dev

- Provide logging config for structured logs; local dev default writes to console
- Provide metrics endpoints (Prometheus) in backend for key metrics
- Use local postgres via docker-compose for dev; scripts/docker-compose.yml referenced in README (not included here)


---

Versioning & branching

- Use GitHub Flow (feature branches, pull requests, code reviews)
- Tag releases semantically (vMAJOR.MINOR.PATCH)


---

Summary

This project structure balances modularity, clarity, and production readiness for the AI Product Feedback Synthesis Assistant. It separates concerns between frontend, backend, infra, and documentation; follows industry conventions for naming and coding standards; and provides a clear configuration and import strategy to support predictable developer experience and safe deployments.

Save this file at: docs/project-structure.md

End of document.
