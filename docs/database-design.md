# Database Design — PostgreSQL (Production-ready)

Project: AI Product Feedback Synthesis Assistant (MVP)

Date: 2026-07-29

This document describes a production-ready PostgreSQL schema design for the MVP. It includes an ER diagram (Mermaid), table definitions, relationships, primary/foreign keys, indexes, constraints, data types, and normalization notes. Each table includes purpose, columns, and relationships.

Design goals
- Deterministic analytics and auditability are first-class concerns.
- Clear separation between immutable snapshots (CSV blobs) and derived entities (feedback items, themes).
- Support AI suggestions as audit-tracked suggestions (not authoritative) with model metadata and prompt history.
- Keep schema normalized (3NF) and add pragmatic indexes for expected queries.
- Provide hooks for vector/embedding storage (pgvector or separate vector DB).

Notes on extensions
- Recommend installing the `pg_trgm` and `pgvector` extensions in PostgreSQL if using full-text similarity and vector embeddings locally.

---

## 1) ER Diagram (Mermaid)

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : has
    USERS ||--o{ INGESTS : uploads
    INGESTS ||--o{ FEEDBACK_ITEMS : contains
    INGESTS ||--o{ CSV_SNAPSHOTS : has
    INGESTS ||--o{ INGEST_JOBS : has
    FEEDBACK_ITEMS ||--o{ THEME_MEMBERSHIPS : member_of
    THEMES ||--o{ THEME_MEMBERSHIPS : includes
    THEMES ||--o{ AUDIT_LOGS : audited
    THEMES ||--o{ REPORT_THEMES : included_in
    REPORTS ||--o{ REPORT_THEMES : contains
    INGESTS ||--o{ AI_JOBS : triggers
    AI_JOBS ||--o{ AI_SUGGESTIONS : produces
    AI_SUGGESTIONS ||--o{ AI_SNIPPETS : uses
    FEEDBACK_ITEMS ||--o{ FEEDBACK_EMBEDDINGS : has
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ REPORTS : generates
    ADMINISTRATORS ||--o{ FEATURE_FLAGS : manages

    %% Entities
    ORGANIZATIONS {
        uuid id PK
        text name
    }
    USERS {
        uuid id PK
        uuid org_id FK
        text email
        text display_name
        text role
    }
    INGESTS {
        uuid id PK
        uuid org_id FK
        uuid uploaded_by FK
        text title
        int total_rows
        timestamp created_at
        text status
    }
    CSV_SNAPSHOTS {
        uuid id PK
        uuid ingest_id FK
        text storage_path
        jsonb schema
        timestamp created_at
    }
    FEEDBACK_ITEMS {
        uuid id PK
        uuid ingest_id FK
        int row_number
        text feedback_text
        text source
        text user_type
        text product_area
        date feedback_date
        numeric rating
    }
    THEMES {
        uuid id PK
        uuid ingest_id FK
        text name
        text status
        text ai_suggested_label
        jsonb metrics_cache
        timestamp created_at
    }
    THEME_MEMBERSHIPS {
        uuid id PK
        uuid theme_id FK
        uuid feedback_item_id FK
    }
    AI_JOBS {
        uuid id PK
        uuid ingest_id FK
        uuid requested_by FK
        text status
        jsonb job_params
        jsonb result_metadata
        timestamp created_at
        timestamp completed_at
    }
    AI_SUGGESTIONS {
        uuid id PK
        uuid ai_job_id FK
        uuid theme_id FK NULL
        text suggested_label
        text suggested_problem_statement
        numeric confidence
        jsonb model_metadata
    }
    AI_SNIPPETS {
        uuid id PK
        uuid ai_suggestion_id FK
        uuid feedback_item_id FK
        text excerpt
    }
    REPORTS {
        uuid id PK
        uuid ingest_id FK
        uuid created_by FK
        text title
        jsonb snapshot
        timestamp created_at
    }
    REPORT_THEMES {
        uuid id PK
        uuid report_id FK
        uuid theme_id FK
        jsonb theme_snapshot
    }
    AUDIT_LOGS {
        uuid id PK
        uuid actor_id FK
        text resource_type
        uuid resource_id
        text action
        jsonb before
        jsonb after
        timestamp created_at
    }
    FEEDBACK_EMBEDDINGS {
        uuid id PK
        uuid feedback_item_id FK
        vector embedding
        timestamp created_at
    }
    FEATURE_FLAGS {
        uuid id PK
        uuid org_id FK
        text key
        bool enabled
    }
```

---

## 2) Tables — Detailed

Note: Use UUID primary keys for global uniqueness; use `uuid_generate_v4()` in Postgres. Timestamps use timestamptz.

1. organizations
- Purpose: Represent customer organization. (MVP may be single org but include for future multi-org support.)
- Columns:
  - id uuid PRIMARY KEY
  - name text NOT NULL
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: users(org_id), ingests(org_id), feature_flags(org_id)
- Indexes: pk on id; index on name (unique or non-unique depending on needs)

2. users
- Purpose: Application users (Analyst, Admin, Viewer).
- Columns:
  - id uuid PRIMARY KEY
  - org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE
  - email text NOT NULL UNIQUE
  - display_name text
  - role text NOT NULL CHECK (role IN ('admin','analyst','viewer'))
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: ingests.uploaded_by, ai_jobs.requested_by, reports.created_by, audit_logs.actor_id
- Indexes: pk, index on org_id, unique index on email
- Notes: Role enum could be implemented with a separate roles table for extensibility.

3. ingests
- Purpose: Track CSV ingestion runs (a logical dataset derived from an uploaded CSV snapshot).
- Columns:
  - id uuid PRIMARY KEY
  - org_id uuid NOT NULL REFERENCES organizations(id)
  - uploaded_by uuid NOT NULL REFERENCES users(id)
  - title text
  - description text
  - total_rows integer NOT NULL DEFAULT 0
  - status text NOT NULL CHECK (status IN ('queued','parsing','ready','failed'))
  - created_at timestamptz NOT NULL DEFAULT now()
  - completed_at timestamptz NULL
- Relationships: csv_snapshots(ingest_id), feedback_items(ingest_id), ai_jobs(ingest_id), reports(ingest_id), themes(ingest_id)
- Indexes: index on org_id, index on status, index on created_at

4. csv_snapshots
- Purpose: Store immutable metadata referencing the original CSV file saved in object storage.
- Columns:
  - id uuid PRIMARY KEY
  - ingest_id uuid NOT NULL REFERENCES ingests(id) ON DELETE CASCADE
  - storage_path text NOT NULL -- e.g., s3://bucket/path.csv
  - filename text
  - content_type text
  - file_size_bytes bigint
  - schema jsonb NULL -- parsed column headers and types
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: each ingest has 1+ snapshots; for MVP typically 1
- Indexes: index on ingest_id
- Constraints: storage_path not null

5. feedback_items
- Purpose: Normalized representation of each feedback row in the CSV. Deterministic analytics operate on this table.
- Columns:
  - id uuid PRIMARY KEY
  - ingest_id uuid NOT NULL REFERENCES ingests(id) ON DELETE CASCADE
  - row_number integer NOT NULL -- original CSV row
  - feedback_text text NOT NULL
  - source text NOT NULL
  - user_type text NOT NULL
  - product_area text
  - feedback_date date NOT NULL
  - rating numeric NULL
  - metadata jsonb NULL -- optional raw row or extracted fields
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: theme_memberships(feedback_item_id), ai_snippets(feedback_item_id), feedback_embeddings(feedback_item_id)
- Indexes:
  - index on ingest_id
  - index on (ingest_id, row_number) unique
  - GIN index on feedback_text using `to_tsvector(...)` for full-text search
- Constraints: unique(ingest_id,row_number)
- Notes: For performance, consider partitioning by ingest_id when expecting very large datasets.

6. themes
- Purpose: Represent curated themes (suggested or human-created) within an ingest.
- Columns:
  - id uuid PRIMARY KEY
  - ingest_id uuid NOT NULL REFERENCES ingests(id) ON DELETE CASCADE
  - name text NOT NULL
  - status text NOT NULL CHECK (status IN ('suggested','approved','rejected','merged','archived'))
  - ai_suggested_label text NULL
  - created_by uuid NULL REFERENCES users(id)
  - created_at timestamptz NOT NULL DEFAULT now()
  - metrics_cache jsonb NULL -- optional precomputed deterministic metrics (counts/distributions/time-series)
  - note text NULL
- Relationships: theme_memberships(theme_id), ai_suggestions(theme_id), report_themes(theme_id), audit_logs(resource_id when resource_type='theme')
- Indexes: index on ingest_id; index on (ingest_id,status); index on name (partial for ingest)
- Constraints: unique(ingest_id,name) to avoid duplicate names in same ingest

7. theme_memberships
- Purpose: Many-to-many mapping between themes and feedback_items. Each row represents an item assigned to a theme.
- Columns:
  - id uuid PRIMARY KEY
  - theme_id uuid NOT NULL REFERENCES themes(id) ON DELETE CASCADE
  - feedback_item_id uuid NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: themes, feedback_items
- Indexes: unique(theme_id,feedback_item_id) ; index on feedback_item_id
- Notes: Use this as authoritative membership for deterministic counts.

8. ai_jobs
- Purpose: Track background AI analysis jobs triggered for an ingest (preprocessing, embedding, LLM calls).
- Columns:
  - id uuid PRIMARY KEY
  - ingest_id uuid NOT NULL REFERENCES ingests(id) ON DELETE CASCADE
  - requested_by uuid REFERENCES users(id)
  - status text NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled'))
  - job_params jsonb NULL -- e.g., cluster_count, thresholds
  - result_metadata jsonb NULL -- summary (time taken, candidate theme count)
  - error jsonb NULL -- capture structured error from model/provider
  - created_at timestamptz NOT NULL DEFAULT now()
  - completed_at timestamptz NULL
- Relationships: ai_suggestions(ai_job_id)
- Indexes: index on ingest_id; index on status

9. ai_suggestions
- Purpose: Store AI-proposed themes and problem statements returned by an AI job. Suggestions are not authoritative and must be approved by humans.
- Columns:
  - id uuid PRIMARY KEY
  - ai_job_id uuid NOT NULL REFERENCES ai_jobs(id) ON DELETE CASCADE
  - theme_id uuid NULL REFERENCES themes(id) -- optional link if suggestion was persisted as a theme
  - suggested_label text
  - suggested_problem_statement text
  - confidence numeric NULL -- 0..1
  - model_metadata jsonb NULL -- model name, prompt hash, token usage
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: ai_snippets(ai_suggestion_id), themes(optional)
- Indexes: index on ai_job_id
- Notes: Keep the prompt and LLM output in model_metadata or separate logging store for AGENT_USAGE.md; beware of sensitive data storage.

10. ai_snippets
- Purpose: Map AI suggestion excerpts to feedback_items (which items the AI used as evidence).
- Columns:
  - id uuid PRIMARY KEY
  - ai_suggestion_id uuid NOT NULL REFERENCES ai_suggestions(id) ON DELETE CASCADE
  - feedback_item_id uuid NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE
  - excerpt text NULL -- AI-chosen excerpt
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: feedback_items, ai_suggestions
- Indexes: index on ai_suggestion_id, index on feedback_item_id

11. feedback_embeddings (optional, for similarity)
- Purpose: Store vector embeddings for feedback items when running similarity operations locally. Alternatively a vector DB can be used.
- Columns:
  - id uuid PRIMARY KEY
  - feedback_item_id uuid NOT NULL REFERENCES feedback_items(id) ON DELETE CASCADE UNIQUE
  - embedding vector NULL -- if using pgvector extension, or float8[] if not
  - model text NULL -- model used to compute embedding
  - created_at timestamptz NOT NULL DEFAULT now()
- Indexes: GIN index on embedding (pgvector) or appropriate index on vector store
- Notes: For production, consider using an external vector DB (Pinecone, Milvus) and store only references here.

12. reports
- Purpose: Persist saved synthesis reports (snapshots) and enable export.
- Columns:
  - id uuid PRIMARY KEY
  - ingest_id uuid NOT NULL REFERENCES ingests(id)
  - created_by uuid REFERENCES users(id)
  - title text NOT NULL
  - description text
  - snapshot jsonb NOT NULL -- complete snapshot of approved themes and metrics at save time
  - include_audit boolean NOT NULL DEFAULT true
  - created_at timestamptz NOT NULL DEFAULT now()
- Relationships: report_themes(report_id)
- Indexes: index on ingest_id, index on created_by

13. report_themes
- Purpose: Store per-theme snapshot details within a report (denormalized to freeze state at report time).
- Columns:
  - id uuid PRIMARY KEY
  - report_id uuid NOT NULL REFERENCES reports(id) ON DELETE CASCADE
  - theme_id uuid NOT NULL REFERENCES themes(id)
  - theme_snapshot jsonb NOT NULL -- name, metrics, supporting item ids/texts
  - created_at timestamptz NOT NULL DEFAULT now()
- Indexes: index on report_id

14. audit_logs
- Purpose: Immutable audit trail for all important actions (theme rename, merge, split, approve, reject, job starts/ends).
- Columns:
  - id uuid PRIMARY KEY
  - actor_id uuid REFERENCES users(id)
  - resource_type text NOT NULL -- e.g., 'theme','ingest','ai_job','report'
  - resource_id uuid NULL
  - action text NOT NULL -- e.g., 'theme.rename','theme.merge','theme.approve'
  - before jsonb NULL
  - after jsonb NULL
  - metadata jsonb NULL -- e.g., reason text, diff, client info
  - created_at timestamptz NOT NULL DEFAULT now()
- Indexes: index on actor_id, index on (resource_type,resource_id), index on created_at
- Constraints: action not null

15. feature_flags
- Purpose: Per-organization toggles for features like AI analysis.
- Columns:
  - id uuid PRIMARY KEY
  - org_id uuid NOT NULL REFERENCES organizations(id)
  - key text NOT NULL
  - enabled boolean NOT NULL DEFAULT false
  - created_at timestamptz NOT NULL DEFAULT now()
- Indexes: unique(org_id,key)

16. ingest_jobs (optional: detailed job tracking)
- Purpose: Track parsing/validation jobs and statuses.
- Columns:
  - id uuid PRIMARY KEY
  - ingest_id uuid NOT NULL REFERENCES ingests(id)
  - job_type text NOT NULL CHECK (job_type IN ('parse','validate','analytics'))
  - status text NOT NULL CHECK (status IN ('queued','running','completed','failed'))
  - error jsonb NULL
  - started_at timestamptz NULL
  - finished_at timestamptz NULL
- Indexes: index on ingest_id, status

17. comments (optional)
- Purpose: Analyst comments on themes or on feedback items.
- Columns:
  - id uuid PRIMARY KEY
  - user_id uuid NOT NULL REFERENCES users(id)
  - resource_type text NOT NULL -- 'theme'|'feedback_item'
  - resource_id uuid NOT NULL
  - body text NOT NULL
  - created_at timestamptz NOT NULL DEFAULT now()
- Indexes: index(resource_type,resource_id), index(user_id)

---

## 3) Relationships (summary)
- organizations 1..* users
- organizations 1..* ingests
- users 1..* ingests (uploaded_by)
- ingests 1..* csv_snapshots
- ingests 1..* feedback_items
- feedback_items *..* themes (via theme_memberships)
- ingests 1..* ai_jobs
- ai_jobs 1..* ai_suggestions
- ai_suggestions 1..* ai_snippets
- ingests 1..* reports
- reports 1..* report_themes
- users 1..* audit_logs (actor)

Referential actions
- ON DELETE CASCADE for ingest -> feedback_items and related child tables to ensure dataset-level cleanup
- Consider ON DELETE RESTRICT for themes when included in reports to avoid accidentally deleting referenced themes used in reports (instead mark 'archived')

---

## 4) Primary Keys
- All primary keys are UUIDs (uuid_generate_v4()) for global uniqueness and safe merging across environments.
- For small lookup tables (roles, feature flags), integer keys are acceptable but UUIDs keep consistency.

---

## 5) Foreign Keys
- Explicit FK constraints on all references as described in table definitions above (users.org_id -> organizations.id, feedback_items.ingest_id -> ingests.id, etc.).
- Foreign keys use ON DELETE CASCADE where child data is logically bound to parent (e.g., when removing an ingest).
- For object references used in audits and reports, prefer to keep references stable; do not cascade deletions for reports -> themes (instead store snapshots in report_themes.jsonb and use ON DELETE RESTRICT or simply archive themes).

---

## 6) Indexes
- Primary key indexes on id columns are automatic.
- Recommended additional indexes (non-exhaustive):
  - users(email) UNIQUE
  - ingests(org_id), ingests(status), ingests(created_at)
  - feedback_items(ingest_id), feedback_items(ingest_id,row_number) UNIQUE
  - feedback_items: GIN index on to_tsvector('english', feedback_text) for full-text search
  - themes(ingest_id,status), themes(ingest_id,name) UNIQUE
  - theme_memberships(theme_id), theme_memberships(feedback_item_id)
  - ai_jobs(ingest_id,status)
  - reports(ingest_id,created_at)
  - audit_logs(resource_type,resource_id), audit_logs(created_at)
  - feedback_embeddings(embedding) GIN/ivfflat depending on pgvector usage

Index considerations
- Use partial indexes where appropriate (e.g., themes WHERE status='approved') to speed common queries.
- For large text search, use GIN trigram or full-text indexes.

---

## 7) Constraints
- NOT NULL on required fields.
- CHECK constraints for enumerated status fields (ingests.status, ai_jobs.status, themes.status).
- UNIQUE constraints: users.email, feedback_items(ingest_id,row_number), themes(ingest_id,name), feature_flags(org_id,key).
- Referential integrity enforced by foreign keys.

---

## 8) Data Types (chosen)
- UUID: uuid (primary keys)
- Text: text (unbounded strings) for feedback_text, labels, problem statements
- Date/time: timestamptz for created_at/completed_at; date for feedback_date if time not relevant
- Numeric counts: integer for counts, numeric for rating/confidence (or real/float8 if acceptable)
- JSONB: for flexible fields like schema, model_metadata, metrics_cache, snapshot
- Vector: `vector` (pgvector) or float8[] for embeddings
- Boolean: boolean

Storage tips
- Store original CSV in object storage (S3) and store only metadata and a path in csv_snapshots.
- Keep heavy LLM outputs but consider retention policy and PII redaction; store prompts and outputs in model_metadata with consideration for privacy.

---

## 9) Normalization
- Schema is normalized to 3NF:
  - feedback_items is a normalized representation of each CSV row (no duplicated theme info)
  - theme_memberships is the associative entity implementing many-to-many between themes and feedback_items
  - ai_suggestions and ai_snippets separate AI outputs from authoritative themes
  - reports and report_themes denormalize snapshots to freeze state at report time

Denormalization
- metrics_cache in themes and theme_snapshot in report_themes are denormalizations for performance and snapshotting. Keep them as JSONB and rebuildable from canonical data.

---

## 10) Example queries (usage patterns)
- Compute theme member count (authoritative):
  SELECT theme_id, COUNT(*) FROM theme_memberships WHERE theme_id = $1 GROUP BY theme_id;

- Get distribution by source for a theme:
  SELECT fi.source, COUNT(*) FROM theme_memberships tm JOIN feedback_items fi ON tm.feedback_item_id = fi.id WHERE tm.theme_id = $1 GROUP BY fi.source;

- Time-series frequency for a theme (weekly):
  SELECT date_trunc('week', fi.feedback_date) AS week, COUNT(*) FROM theme_memberships tm JOIN feedback_items fi ON tm.feedback_item_id = fi.id WHERE tm.theme_id = $1 GROUP BY week ORDER BY week;

- Full-text search for feedback items containing "crash":
  SELECT id, feedback_text FROM feedback_items WHERE to_tsvector('english', feedback_text) @@ plainto_tsquery('english', 'crash');

- Find AI suggestions matching historical themes (using embeddings vector similarity if FE supported)

---

## 11) Operational considerations
- Migrations: use a migration tool (Flyway, Liquibase, or node/ts migration tool) and ensure non-blocking schema changes. Add new columns with defaults as nullable then backfill.
- Backups & retention: schedule nightly backups; retention according to org policy. Archive old ingests and snapshots after configured retention.
- Data retention & PII: enforce retention policies; provide data deletion endpoints per GDPR/CCPA.
- Metrics & monitoring: track table sizes, slow queries, index bloat, and query plans. Setup alerts on long-running ETL/AI jobs.

---

## 12) Summary of Key Tables and Purpose
- organizations: tenant metadata
- users: system users and roles
- ingests: metadata about each uploaded CSV dataset
- csv_snapshots: object-store metadata for raw CSV files
- feedback_items: canonical, normalized rows used for analytics
- themes: curated groups with status and cached metrics
- theme_memberships: authoritative mapping from themes to feedback items
- ai_jobs, ai_suggestions, ai_snippets: full traceability of AI analysis and evidence
- reports, report_themes: snapshot and exportable reports
- audit_logs: immutable audit trail of user and system actions
- feedback_embeddings: optional local embedding store for similarity

---

End of database design document.
