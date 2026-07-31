# AI Product Feedback Synthesis Assistant

Backend-only FastAPI service for immutable CSV ingest and deterministic theme analytics. It accepts the case-insensitive headers `feedback text`, `source`, `user type`, `product area`, `date`, and optional `rating`.

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies: `pip install -r backend/requirements.txt`.
3. Copy `backend/.env.example` to `backend/.env`. SQLite is the default; use a SQLAlchemy-compatible `DATABASE_URL` for another provider. Set `GEMINI_API_KEY` only to enable evidence-first suggestion jobs.
4. From `backend`, run `alembic upgrade head`.
5. Start the API with `uvicorn app.main:app --reload`.

Run tests from `backend` with `pytest`.

The API exposes `POST /api/v1/ingests`, `POST /api/v1/ingests/{ingest_id}/analysis`, `GET /api/v1/ingests/{ingest_id}`, and `GET /api/v1/themes/{theme_id}`. Gemini can create only evidence-cited `AI suggested` themes; it cannot calculate metrics or approve themes. Theme metrics remain calculated only from persisted theme-membership evidence.
