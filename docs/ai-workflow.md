# AI Workflow Specification

Project: AI Product Feedback Synthesis Assistant (MVP)

Date: 2026-07-29

Author: Senior AI Architect

---

This document defines the AI workflow for the AI Product Feedback Synthesis Assistant. It describes an end-to-end processing pipeline, data handling, model interactions, prompt engineering, response schema, logging, and failure recovery. It also distinguishes responsibilities between AI and backend systems.

Critical safety rules (non-negotiable)
- The AI must never calculate or assert deterministic statistics (counts, distributions, aggregates). All numeric summaries must be computed by deterministic backend code and displayed as authoritative.
- The AI must never invent counts or priorities. Any numeric suggestion in AI output must be labeled as "suggested" and must not be used as authoritative data in reports.
- The AI must always cite original feedback items (by feedback_item_id and excerpt) for every theme and conclusion it produces.
- Human sign-off is required for any theme to be marked Approved.

Section structure
1. AI Workflow Overview
2. End-to-End AI Processing Pipeline
3. CSV Input Processing
4. Data Cleaning Strategy
5. Theme Extraction Strategy
6. Semantic Grouping Strategy
7. Recurring Issue Detection
8. Isolated Issue Detection
9. Historical Theme Comparison
10. Problem Statement Generation
11. Evidence Mapping
12. Confidence Score Strategy
13. Human Review Workflow
14. Hallucination Prevention Strategy
15. Prompt Engineering Strategy
16. JSON Response Schema
17. Retry Strategy
18. Logging Strategy
19. Failure Recovery
20. Performance Considerations

Throughout, responsibilities are split into two categories:
- AI Responsibilities — what the LLM/embedding models handle.
- Backend Responsibilities — deterministic computation, data management, security, and orchestration.

---

1. AI Workflow Overview

Purpose
- Use embeddings, clustering, and LLM capabilities to convert unstructured feedback into suggested themes, candidate problem statements, highlight supporting evidence, and suggest similarity to historical themes. The AI provides candidates and explanations; humans remain the authority.

High-level flow
1. Backend prepares cleaned, token-limited text payloads and computes deterministic analytics.
2. Embedding service computes vectors for feedback items and, optionally, for historical notes.
3. Clustering/semantic grouping engine proposes candidate clusters (themes) using vector similarity (backend) and outputs cluster assignments.
4. For each candidate theme, an LLM is invoked (controlled prompt) to draft a concise problem statement and to extract snippet-level rationale.
5. AI outputs are persisted as suggestions with model metadata and linked to feedback_item_ids.
6. Analysts review suggestions in UI and perform rename/merge/split/approve actions. Backend records all audit trail entries.

Security and safety
- Redact or transform PII per org-level policy before any external LLM or third-party embedding call.
- Store prompts, model outputs, and metadata in secure storage with restricted access and retention policy.


AI Responsibilities (summary)
- Produce suggested theme labels and human-readable problem statements.
- Provide explainable evidence: list of feedback_item_ids and short excerpts that justify inclusion in a theme.
- Provide similarity scores (relative) for matching against historical themes — not counts.
- Provide natural-language rationales and highlight potential edge cases to help human reviewers.

Backend Responsibilities (summary)
- Compute all deterministic statistics (counts, distributions, time series) and persist them as authoritative.
- Orchestrate jobs (enqueue, worker), pre-process and redact data, compute embeddings, run clustering, and call LLMs.
- Persist raw model inputs/outputs, and enforce retention and access policies.
- Manage retries, DLQs, and job monitoring.

---

2. End-to-End AI Processing Pipeline

Pipeline stages (ordered)
1. CSV ingestion and snapshot (backend)
2. Deterministic parsing and validation (backend)
3. Preprocessing & redaction (backend)
4. Text normalization and optional deduplication (backend)
5. Embedding generation (backend or embedding service)
6. Vector-based semantic grouping/clustering (backend)
7. Candidate cluster refinement and pruning (backend)
8. LLM drafting (prompted) for each cluster (AI)
9. Evidence mapping from LLM outputs to feedback_item_ids (AI + backend validation)
10. Persist AI suggestions (backend) and compute authoritative metrics (backend)
11. UI presentation and human review (frontend/backend)

Notes
- Steps 5-7 (embedding and clustering) must be deterministic or use deterministic seeds where possible to ensure reproducible candidate clusters for the same inputs.
- LLM calls are non-deterministic; store seed, prompt, model version, and tokens used for auditing.

---

3. CSV Input Processing

Backend Responsibilities
- Parse CSV and create feedback_items records with canonical fields: feedback_text, source, user_type, product_area, feedback_date, rating, row_number.
- Validate required columns and row-level constraints. Produce a downloadable error report for failures.
- Snapshot original CSV in object store and store parsed schema.
- Store raw text in feedback_items.metadata for traceability.

AI Responsibilities
- None. The AI must not be used to parse or correct CSVs in the MVP; any suggested corrections must pass through human review.

Preprocessing (backend)
- Trim whitespace, normalize unicode, remove null-control characters.
- Limit text length per item to an application-configurable max token budget (e.g., 1024 tokens) and store truncated versions with an indicator.
- Redact PII fields where required by org policy before sending to external services (embedding/LLM). PII redaction should preserve minimal context for meaning (e.g., replace email with [EMAIL_REDACTED]).
- Produce a `clean_text` field used for embeddings and LLM inputs.

Deduplication
- Compute a simple checksum (sha256) of cleaned text to identify exact duplicates; flag duplicates and let backend decide whether to include duplicates in embeddings or deduplicate before clustering.

---

4. Data Cleaning Strategy

Goals
- Maximize signal-to-noise for both embedding and LLM processing while preserving citation fidelity.

Steps (backend)
1. Normalize punctuation and whitespace; collapse long whitespace sequences.
2. Remove or normalize common boilerplate tokens (e.g., "Thanks", "Regards") optionally for embeddings.
3. Lowercase only for embeddings pipeline; keep original casing for UI presentation and citations.
4. Token-limit: truncate to N tokens for embeddings/LLM input but store full raw text for citation and audit.
5. Replace known PII patterns (email, phone, SSN-like) with redaction tokens — configurable by org.
6. Strip out long quoted content (e.g., email threads) or present them as single items if they exceed token budget; surface truncation flag in UI.

AI Responsibilities
- Suggest normalization heuristics in system prompts or as configuration, but do not alter raw stored inputs.

Validation
- Store both `raw_text` and `clean_text` in DB; all citations reference raw_text and row_number.

---

5. Theme Extraction Strategy

Overview
- Use vector embeddings and clustering as the primary method to group semantically related feedback into candidate themes. Follow with LLM summarization for human-readable labels and problem statements.

Backend Responsibilities
- Compute embeddings for each feedback_item using a chosen embedding model (local or provider) and store vector reference.
- Run clustering algorithms (e.g., HDBSCAN, Agglomerative, or k-means with elbow method) with deterministic seeds and parameters.
- Produce candidate clusters with minimum and maximum thresholds (min_items, max_cluster_size). Prune clusters below min threshold and mark small clusters as "isolated" candidates.

AI Responsibilities
- Given cluster item text (or excerpts) and a small context (ingest-level metadata), generate suggested label and problem statement, list supporting item excerpts, and flag potential ambiguous items.

Partitioning
- Run clustering at multiple granularities (high-level clusters then subclusters) to produce hierarchical theme candidates if dataset size permits.

Human-in-loop
- All suggested clusters are presented to Analysts for review; operators may accept, rename, merge clusters.

---

6. Semantic Grouping Strategy

Goals
- Group feedback by semantic similarity robust to paraphrase and synonyms.

Techniques (backend)
- Use embeddings from a semantic model (sentence-transformers or provider embeddings). Store vectors centrally.
- Compute pairwise distances and run density-based clustering (HDBSCAN recommended for variable-sized clusters) to find dense regions representing recurring themes.
- Use approximate nearest neighbor (ANN) indexes for scale (FAISS, Milvus, or pgvector ivfflat).
- After initial cluster assignment, run a small deterministic re-ranking step that removes outliers (items with low median similarity to cluster centroid) and optionally moves them to nearest cluster if above threshold.

AI Responsibilities
- For each cluster, produce a short human-friendly theme label and problem statement and identify top-k representative snippets for evidence mapping.

Edge cases
- Overlapping clusters: maintain candidate overlap using soft assignments; store membership score per item if necessary. Final authoritative membership must come from theme_memberships table after human curation.

---

7. Recurring Issue Detection

Definition
- Recurring issues are themes with multiple independent feedback items expressing the same underlying problem.

Backend Responsibilities
- Use cluster sizes as a raw indicator of recurrence (but do not expose raw counts as AI outputs). Compute frequency over time using row feedback_date to produce trend lines.
- Detect rising trends: compute time-series slope or moving average increase and flag clusters with statistically significant upticks.

AI Responsibilities
- Provide natural-language description of recurrence patterns (e.g., "Many users over the past 2 weeks mentioned X"), but always include the authoritative backend time-series chart and never invent numeric counts. If the AI references numbers, label them as suggested and recommend the reviewer check deterministic analytics.

---

8. Isolated Issue Detection

Definition
- Isolated issues are clusters with few members (below min threshold) or single-shot comments.

Backend Responsibilities
- Mark clusters under `min_items` as isolated and compute whether they are duplicates of larger clusters by similarity scan.

AI Responsibilities
- Explain why cluster is isolated and provide examples (citations). Suggest whether to discard, hold, or merge with another theme, but do not make the final decision.

---

9. Historical Theme Comparison

Purpose
- Compare newly suggested themes to a set of historical themes or product notes to surface repeats and reduce duplicate work.

Backend Responsibilities
- Maintain a historical-themes collection with precomputed embeddings (from past reports or provided notes). Use ANN search to find nearest historical themes for each new candidate cluster.
- Compute similarity measures (cosine similarity) and return top-N historical matches with similarity score.

AI Responsibilities
- Given the historical matches and their textual descriptions, produce a short natural-language mapping and note differences; always include direct links to historical theme ids and citations. Do not assert that the new theme is X — present as a similarity suggestion.

Presentation
- UI shows historical match list with similarity score from backend and LLM-provided commentary.

---

10. Problem Statement Generation

Goal
- Produce a concise problem statement in plain language that describes the core user problem represented by a theme.

AI Responsibilities
- Given up to K representative excerpts and ingest/product context, draft 1-3 short candidate problem statements (20-40 words each) and suggest supporting evidence (feedback_item_ids + excerpts).
- Provide a short rationale for each wording choice and indicate ambiguous or multi-topic aspects to watch.

Backend Responsibilities
- Provide AI with sanitized excerpts and cluster metadata, enforce token limits, and persist AI outputs and metadata.
- Ensure AI outputs are stored as suggestions and never promoted without human approval.

Constraints
- Problem statements must include citations (list of feedback_item_ids) and must not include numeric assertions about counts or frequencies.

---

11. Evidence Mapping

Purpose
- Map AI statements to explicit supporting feedback items so reviewers can verify claims.

AI Responsibilities
- For each generated statement, list supporting snippets and their corresponding feedback_item_ids (minimum 1, max configurable). Each snippet includes raw_text excerpt (<=250 chars) and row_number.

Backend Responsibilities
- Validate that every feedback_item_id cited by AI exists in the ingest and that excerpt is a substring of the raw_text; if not, mark suggestion as invalid and flag for manual review.
- Store the validated mapping in ai_snippets table.

Presentation rules
- UI displays citations next to each theme and problem statement with links to the original CSV row.

---

12. Confidence Score Strategy

Purpose
- Provide a measure of how confident the system is that the suggested theme/problem statement is coherent and supported.

AI Responsibilities
- Provide an internal confidence estimate (0..1) for each suggestion derived from model outputs (softmax, heuristics). This is a relative guidance only.

Backend Responsibilities
- Compute and display objective signals that can be used alongside AI confidence: cluster cohesion (avg pairwise similarity), number of distinct sources in cluster (authored by backend), time-span covered by items.
- Display AI confidence as "Suggestion confidence" with a tooltip explaining it is model-based and not authoritative.

Important
- Confidence scores are advisory; do not use them to auto-approve or auto-prioritize themes.

---

13. Human Review Workflow

Overview
- Analysts review suggested themes and perform actions: rename, merge, split, reject, approve.

Procedure
1. Analyst opens Theme Review for ingest.
2. For each suggested theme, analyst inspects deterministic metrics (member_count, distributions, time-series) computed by backend and AI-supplied problem statements + evidence.
3. Analyst may edit theme name, adjust membership (split/merge), and add notes. All changes recorded in audit_logs.
4. Approve requires explicit confirmation; approved themes are included in saved reports.

AI Responsibilities
- Provide suggested edits and highlight risky or ambiguous items to speed review.

Backend Responsibilities
- Enforce that approval is a human action and write audit entries. Recompute deterministic metrics after any change to membership.

UI rules
- Show both AI suggestion and authoritative metrics side-by-side.
- Highlight AI-suggested text as "Suggested by AI — review required." Include model metadata link in advanced view.

---

14. Hallucination Prevention Strategy

Principles
- Never allow AI outputs to replace validated data.
- Require evidence linking for every claim.

Implementation
- Enforce evidence mapping: the LLM must cite feedback_item_ids for each theme and problem statement. Backend validates the citation.
- Disallow numeric claims in AI-only content. If AI produces a numeric claim, backend strips or annotates it clearly as "model-suggested" and shows authoritative number from deterministic analytics.
- Input redaction: remove sensitive PII before sending to LLM.
- Use prompt templates that instruct the model explicitly to avoid inventing facts and to include source citations.
- Post-process LLM output with regex and validation checks to detect improbable outputs (e.g., invented row ids or citations) and flag them.

Monitoring
- Monitor model hallucination rate (percentage of suggestions failing validation) and trigger alerts if exceeding thresholds.

---

15. Prompt Engineering Strategy

Goals
- Create compact, deterministic prompts that produce consistent, auditable outputs and require citations.

Prompt template elements
- System prompt (fixed): Communicate role and strict rules: "You are a summarization assistant. You must only use the provided excerpts. For each theme you propose, include: suggested_label, suggested_problem_statement (1-2 sentences), supporting_excerpts (list of feedback_item_id and 1-sentence excerpt). Do NOT invent numbers. Do NOT invent feedback items. Mark uncertain statements explicitly with [UNCERTAIN]."
- Few-shot examples: include 2-3 structured examples mapping excerpts to desired JSON output.
- Max token budget: send the smallest sufficient context to the model — representative excerpts per cluster + cluster-level metadata (e.g., product area).
- Output format instruction: instruct the model to produce valid JSON that matches the JSON response schema. Provide an exact schema snippet in the prompt to minimize parsing errors.

Prompt hygiene
- Sanitize embedded excerpts to escape quotes, preserve necessary punctuation, and limit length.
- Use a prompt hash or version id for traceability; store the hash with model metadata.

Model selection
- Prefer models known for instruction-following and controllability. Use few-shot or system-level instructions to enforce constraints.
- For privacy-sensitive orgs, prefer a self-hosted LLM or private provider.

---

16. JSON Response Schema

AI outputs must conform to a strict JSON schema. Backend will validate and reject outputs that do not match.

Top-level structure (example):

{
  "ai_job_id": "uuid",
  "ingest_id": "uuid",
  "model": {
    "name": "string",
    "version": "string",
    "prompt_hash": "string"
  },
  "suggestions": [
    {
      "suggestion_id": "uuid-local",
      "candidate_cluster_id": "string-or-number",
      "suggested_label": "string",
      "suggested_problem_statement": "string",
      "confidence": 0.0-1.0,
      "evidence": [
        { "feedback_item_id": "uuid", "excerpt": "string", "row_number": integer }
      ],
      "notes": "string (optional)"
    }
  ],
  "metadata": {
    "generated_at": "timestamp",
    "num_candidates": integer
  }
}

Validation rules
- `suggestions` must be an array (may be empty).
- Each evidence item must include a valid feedback_item_id that the backend can verify belongs to the ingest; excerpt must be substring of the stored raw_text for that item.
- `confidence` optional but if present must be numeric between 0 and 1.
- No numeric counts or distributions allowed; if included, backend will ignore and log a warning.

Storage
- Persist entire JSON response in ai_jobs.result_metadata and store normalized entries in ai_suggestions and ai_snippets after validation.

---

17. Retry Strategy

Principles
- Separate transient errors (network, provider rate limits) from permanent errors (invalid input, prompt misformatting).

Backend Responsibilities
- For transient errors from embedding or LLM provider, implement exponential backoff retries with capped attempts, and then send job to DLQ with error diagnostics.
- For validation failures (model output not matching schema), do a small number of retries with adjusted prompt (ask model to reformat strictly) before failing and exposing the output for manual inspection.
- Keep retry count configurable and log each attempt with timestamps and response snippets.

AI Responsibilities
- Support a reformatting prompt that asks the model to output strictly valid JSON if initial output is malformed.

---

18. Logging Strategy

What to log
- Job-level metadata: ai_job_id, ingest_id, requested_by, job_params, created_at, completed_at, status
- Model metadata: model name, version, prompt_hash, token usage, response latency
- Raw prompt and sanitized prompt (redacted) saved in secure logs; raw LLM outputs saved with access controls and retention policy
- Validation results: whether output passed schema checks and any issues found
- Evidence mapping validations and any mismatches
- Retry attempts and error codes

Storage and access
- Store logs in structured logging facility (ELK/Loki/CloudLogging) and persist ai_job result JSON in DB for audit.
- Restrict access to model outputs and prompts to Admins and authorized reviewers only.
- Implement retention policies to purge raw LLM outputs after configured period unless preserved for compliance.

Monitoring
- Track metrics: job success rate, average latency, hallucination rate (invalid evidence), retry rate, token usage costs.

---

19. Failure Recovery

Scenarios and steps
- Embedding provider outage: fallback to cached embeddings for recent ingests or queue jobs until provider available. Fail fast if no fallback and notify Admin.
- LLM provider rate-limit: implement queueing and backoff; surface ETA to user and provide "Run in background" option.
- Schema validation failure for model outputs: attempt reformat retry (1-2 attempts) with stricter prompt. If still failing, mark suggestion as failed and surface raw output for manual curation.
- Partial success (some clusters processed): persist successful suggestions and mark job as partially successful; report errors per cluster.

User-facing behavior
- For long-running jobs, show progress and partial results where validated.
- On failure, provide clear remediation options: Retry, Disable AI (Admin), or Export for manual analysis.

---

20. Performance Considerations

Throughput targets (MVP)
- Single ingest size: up to 10k rows
- Target embedding throughput: process 10k items in < 10 minutes with batch embedding (depends on provider)
- LLM passes: small number of calls per cluster (1-3) — optimize by sending representative snippets rather than full cluster text

Optimization strategies
- Batch embedding calls and cache repeated embeddings across ingests
- Use ANN indexes for clustering and neighbor search to avoid O(N^2) pairwise operations
- Use sampling for large clusters when generating prompts; pick top representative items by similarity to centroid
- Use smaller, cost-effective models for embeddings and use larger instruction-following model only for final drafting

Cost control
- Feature-flag heavy AI usage; expose usage dashboards and per-org quotas
- Token budget enforcement on client-side and server-side; fail gracefully when budget exceeded

Scalability
- Workers horizontally scalable; ensure stateless worker design for embeddings and LLM calling
- Shard vector index across nodes or use managed vector DB for scale

---

Appendix A: Example prompt skeleton (for engineers)

System prompt (fixed):
"You are a synthesis assistant. You will be provided with a short list of feedback excerpts and identifiers. For each candidate cluster, produce a JSON object matching this schema: {suggested_label, suggested_problem_statement, evidence:[{feedback_item_id, excerpt, row_number}], confidence:float}. Do NOT invent feedback_item_ids, counts, or numeric claims. Cite only the provided feedback_item_ids. If unsure, mark fields with [UNCERTAIN]. Output only valid JSON."

User prompt (per cluster):
- include ingest-level context (product area), cluster id, up to K sanitized excerpts (feedback_item_id + excerpt)
- include explicit schema block and required validation rules

Appendix B: Example AI JSON output (valid)

{
  "ai_job_id": "...",
  "ingest_id": "...",
  "model": { "name":"gpt-4o-mini","version":"2026-01-01","prompt_hash":"abc123" },
  "suggestions": [
    {
      "suggestion_id": "sugg-1",
      "candidate_cluster_id": "cluster-12",
      "suggested_label": "Confusing onboarding flow",
      "suggested_problem_statement": "New users struggle to find the feature setup and abandon before completing onboarding.",
      "confidence": 0.78,
      "evidence": [ { "feedback_item_id": "f-111", "excerpt": "I couldn't find how to add my first project", "row_number": 12 } ]
    }
  ],
  "metadata": { "generated_at": "2026-07-29T15:00:00Z", "num_candidates": 12 }
}

---

Document governance
- Store this AI workflow spec in docs/ and version it with changes.
- For changes in model or prompt templates, update prompt_hash and log justification in AGENT_USAGE.md.

End of AI Workflow Specification.
