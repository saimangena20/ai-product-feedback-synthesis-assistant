# UI / UX Specification — MVP

Project: AI Product Feedback Synthesis Assistant

Version: MVP

Date: 2026-07-29

Author: Product Designer / Frontend Architect

---

This document describes the complete user experience for the MVP. It is intended for product, design, and engineering teams to implement the UI without ambiguity. No implementation code is included.

Contents
1. Application Navigation
2. Complete User Flow
3. Screen Flow Diagram (text)
4. Dashboard Layout
5. CSV Upload Page
6. AI Analysis Progress Page
7. Theme Review Page
8. Report Page
9. Empty States
10. Loading States
11. Error States
12. Success States
13. Modal Dialogs
14. Notifications
15. Theme Merge Flow
16. Theme Split Flow
17. Theme Rename Flow
18. Theme Approval Flow
19. Responsive Design Guidelines
20. UI Components List

Design principles
- Evidence-first: every theme links to original feedback. Deterministic numbers are authoritative.
- Human-in-the-loop: AI suggestions are labeled and require human approval.
- Minimal friction: clear states, progressive disclosure, and consistent affordances for actions.
- Auditability: record every state change with visible provenance.

Common conventions
- Primary color: action CTAs (Upload, Approve) — high contrast.
- Secondary color: non-destructive actions (Rename, Comment).
- Danger color: destructive actions (Reject, Delete) with confirming dialog.
- Icons: use standard iconography for upload, search, filter, export, and status.
- Typography: H1 / H2 / H3 for page titles and sections; body size for content and table rows.

---

1. Application Navigation

Purpose
- Provide quick access to primary areas: Dashboard, Uploads, Themes, Reports, Admin (if Admin role), and Help/Docs.

Structure
- Top navigation bar (Global): left-aligned product logo + product name; center-left primary navigation; right-aligned user menu.
- Primary nav items (left-to-right): Dashboard, Upload CSV, Themes, Reports.
- Secondary/admin items (right, visible to Admins): Admin Panel, Historical Themes.
- User menu (right): Profile, Settings, Sign out.
- Breadcrumbs: Theme Review and Report pages include breadcrumbs: Dashboard / Uploads / [Ingest name] / Themes / [Theme name].
- Keyboard shortcuts: 
  - G D -> go to Dashboard
  - G U -> Upload CSV
  - G T -> Themes
  - G R -> Reports

Navigation behaviour
- Active nav item highlighted with primary color and underline.
- Mobile: collapse to hamburger menu at <= 768px.


2. Complete User Flow

High-level flow
1. Sign in -> Dashboard
2. Upload CSV -> validation -> ingest snapshot created
3. Deterministic analytics computed and displayed
4. Optionally trigger AI analysis (or it runs automatically if feature flag on)
5. AI creates suggested themes -> Analyst opens Theme Review
6. Analyst inspects supporting feedback and deterministic metrics
7. Analyst renames / merges / splits / rejects / approves themes
8. Analyst saves reviewed synthesis report -> exports JSON/CSV (PDF optional)
9. Admin can upload historical themes and toggle AI feature flag

Edge flows
- Validation error on CSV: show validation details; analyst corrects and re-uploads or continues with warnings.
- AI job failure: show error with retry button and logs (if available).
- Merge conflict (concurrent edits): show conflict dialog and require resolution.


3. Screen Flow Diagram (text)

- Sign In
  -> Dashboard
    -> Upload CSV
      -> CSV Validation Result
        -> Ingest Detail (Deterministic Analytics)
          -> Trigger AI Analysis (optional)
            -> AI Analysis Progress Page
              -> AI Results (Suggested Themes)
                -> Themes List / Theme Review Page
                  -> Theme Detail
                    -> Actions: Rename | Merge | Split | Reject | Approve
                      -> Update persisted and audit log
                        -> Saved Synthesis Report (Reports Page)
                          -> Export (JSON/CSV/PDF)

Admin flows:
- Dashboard -> Admin Panel -> Historical Themes Upload
- Dashboard -> Admin Panel -> Feature Flags (AI ON/OFF)


4. Dashboard Layout

Purpose
- Central overview of recent ingests, status, quick actions, and summary metrics.

Priority content
- Top bar with 'Upload CSV' CTA and search.
- Recent ingests list (left column) with status chips and quick actions.
- Summary cards (top-right) with counts: Last ingest rows, Suggested themes, Approved themes, Rejected themes.
- Recent reports list (bottom) with links to open or export.

Layout (desktop)
- Two-column layout:
  - Left (60%): Recent ingests, each row shows ingest name, uploaded by, date, status chip, item count, suggested themes count, link to Ingest Detail.
  - Right (40%): Summary cards stacked; below cards, Recent Reports list.

Elements
- Header: "Dashboard" H1; subtitle: "Upload feedback CSVs, review AI suggestions, and export synthesis reports.".
- Search bar: top-left under header to search ingests/themes.
- Quick CTA row: Upload CSV (primary), View Reports (secondary).

Ingest row contents
- Filename or ingest title
- Uploaded by, timestamp
- Status chip: Queued / Parsing / Ready / Failed
- Item count badge
- Suggested themes count badge (if AI enabled)
- Actions dropdown: View, Export, Delete (delete only by Admin)

Expected results
- Clicking ingest row -> Ingest Detail Page
- Clicking Upload -> CSV Upload Page


5. CSV Upload Page

Purpose
- Allow Analyst to upload and validate CSV inputs for synthesis.

Inputs
- File chooser (drag & drop) accepting .csv
- Optional: ingest title text input (default = file name)
- Optional: description text area
- Visibility: Project/organization (single-org for MVP)

Buttons
- Primary: Upload & Parse
- Secondary: Cancel

Tables/Cards/Charts
- After upload, preview card showing first 10 rows in a small table with columns: Row ID, feedback text (truncated), source, user type, product area, date, rating.
- Validation panel (right or below): list of header errors and row-level errors.

Actions
- Upload triggers server-side ingest job and returns job id; local UI shows progress.
- If validation errors found: show 'Fix & Retry' and 'Continue with Warnings' buttons.

Validation
- Required headers present (exact names or accepted synonyms)
- Date format parseable; required fields non-empty
- Row-level errors include row number and message

Expected Results
- On success: redirect to Ingest Detail page with job id and message "CSV parsed and snapshot saved".
- On failure: keep user on upload page with error list and suggested fixes.

Accessibility
- File chooser supports keyboard and screen-reader instructions. Drag-and-drop area has fallback 'Choose file' button.


6. AI Analysis Progress Page

Purpose
- Show status and progress of background AI jobs for a selected ingest.

Primary elements
- Job progress bar: percent complete and estimated time if available.
- Steps timeline: Queue -> Preprocessing (embedding) -> LLM call -> Clustering -> Results persisted.
- Logs / messages panel with timestamps (collapsible).
- Retry button and cancel button (if queued/running).

Inputs
- None (passive). Admin can toggle to cancel or retry.

Buttons
- Cancel Analysis
- Retry Analysis (on failure)
- View Interim Results (if available)

Tables/Cards/Charts
- If partial results available: small 'preview' card for suggested themes count and top 3 theme labels.

Actions
- Polling or WebSocket updates for progress.
- On completion -> link to Themes List / Theme Review Page.

Validation
- Show clear error if LLM call failed along with suggested remediation (check feature flag, quotas).

Expected Results
- On success: navigation option "Open Suggested Themes".
- On failure: actionable error with retry.


7. Theme Review Page

Purpose
- Primary workspace for Analysts to inspect AI-suggested themes, verify evidence, and curate final themes.

Layout
- Three-column responsive layout (desktop):
  - Left: Themes list (Suggested / Approved / Rejected filters) with compact counts
  - Middle: Theme Detail (selected theme) with problem statement, metrics, and actions
  - Right: Supporting feedback list (paginated) with filters and search

Per-page Purpose & elements

A) Themes list (Left column)
- Purpose: quick navigation across themes
- Items: Theme name, status chip (Suggested/Approved/Rejected), member count badge, small sparkline of time-series frequency
- Actions per theme: Select, Context menu (Rename, Merge selection, Reject, Approve)
- Filtering controls: All / Suggested / Approved / Rejected; search by theme name; sort by count or recency

B) Theme Detail (Center column)
- Purpose: show AI suggestion, deterministic metrics, and allow curator actions
- Content:
  - Header: Theme name (editable inline), status badge, approve/reject buttons
  - AI suggestion panel: suggested problem statement (labeled 'AI suggested'), confidence score, explainability notes
  - Deterministic metrics card: member count (authoritative), distribution by source (pie), distribution by user type (bar), time-series chart (small line)
  - Actions row: Rename, Merge, Split, Reject, Approve, Export theme (CSV)
  - Audit trail preview: last 5 audit events for this theme with link to full audit

C) Supporting feedback (Right column)
- Purpose: evidence view
- Table columns: Row ID, Full feedback text (expand/collapse), source, user type, product area, date, rating, selection checkbox
- Actions per row: View in raw CSV (open), Add comment, Mark as noise
- Bulk actions: Add selected to new theme (split), Remove from theme, Flag for review
- Pagination and page-size control

Validation
- Any action that mutates themes must show confirmation (Approve, Reject, Merge, Split) and be transactional.

Expected results
- After Approve: theme status updates to Approved, timestamp and user captured, theme remains visible in Approved filter
- After Merge/Split: member counts and distributions update; audit log entry recorded

Notes on UI behavior
- Inline edit for theme name: click pencil to enable field, Enter to save, Esc to cancel; save triggers API rename and updates audit.
- Approve button: primary green action; approval triggers modal for optional note to include in report.


8. Report Page

Purpose
- List saved synthesis reports and allow view/export.

Layout
- Left: Reports list with metadata (dataset name, generated by, date, number of approved themes)
- Right: Report preview when report selected

Report preview contents
- Header with report title, dataset, generated date, exported by
- Table of approved themes: theme name, member count, distributions (small inline charts), and link to view supporting citations
- Export actions: Download JSON, Download CSV, Generate PDF (if implemented)

Inputs
- Report title (on save), optional description

Buttons
- Save Report (during review), Re-generate (if underlying data changed), Export

Validation
- Save requires at least one approved theme (otherwise show validation message)

Expected results
- Downloaded files include deterministic metrics and raw citations; JSON includes audit excerpt and AI suggestion texts labeled.


9. Empty States

General guidance
- Provide clear guidance on next steps and links to sample CSVs or help docs.
- Use concise microcopy and a single primary CTA.

Examples
- Dashboard empty (no ingests): "No ingests yet"; CTA: "Upload your first CSV"; link to sample CSV and onboarding guide.
- Themes empty: "No suggested themes found"; CTA: "Run AI analysis" or "Upload CSV" depending on context.
- Reports empty: "No saved reports"; CTA: "Save a synthesis report".


10. Loading States

General principles
- Use skeleton loaders where possible; show partial cached data if available.
- For long-running background tasks, show progress percentage and descriptive step text.

Examples
- Table skeleton rows for feedback list
- Placeholder chart with spinner and "Computing metrics" text
- Button-level loading indicators for actions (Approve, Merge)


11. Error States

Principles
- Show clear error message, helpful remediation and a retry action where applicable.
- Log error details to structured logs and surface a friendly message with an error code.

Examples
- CSV parse error: list specific row problems and provide "Download error report".
- AI job failure: show "AI analysis failed" with details: model error / quota / timeout and actions: Retry or Turn off AI.
- Merge conflict: "Merge failed due to concurrent edit" with button "View conflict" showing conflicting theme states.


12. Success States

Principles
- On successful operations show brief confirmation toast plus persistent state change on screen.

Examples
- "CSV successfully uploaded" toast with link to Ingest Detail
- "Theme approved" toast; theme status updated and included in report export
- "Report saved" toast with link to Reports page


13. Modal Dialogs

Modal style
- Title, brief description, required input controls, primary & secondary actions, cancel on outside click and Esc, but destructive actions require explicit confirm button.

List of modals

A) Confirm Approve
- Purpose: confirm approval and optional note
- Inputs: optional text area for note
- Buttons: Approve (primary), Cancel
- Validation: none
- Expected: persists approve action, records audit event, closes modal

B) Confirm Reject
- Purpose: require reason for rejecting a theme
- Inputs: required reason text area (min 10 chars)
- Buttons: Reject (danger), Cancel
- Validation: reason required
- Expected: theme marked Rejected, stored reason in audit

C) Merge Themes
- Purpose: confirm merging multiple themes
- Inputs: select target theme name (text input prefilled with first selected target), checkbox to preserve original theme ids in notes
- Buttons: Merge (primary), Cancel
- Validation: at least two themes selected
- Expected: merged theme created or target updated, audit recorded

D) Split Theme
- Purpose: create a new theme from selected items
- Inputs: new theme name (required), optional description
- Buttons: Create (primary), Cancel
- Validation: at least 1 feedback item selected and name required
- Expected: new theme created; counts updated; audit recorded

E) CSV Validation Errors
- Purpose: show parsed validation errors and allow user to continue with warnings or cancel
- Inputs: none
- Buttons: Fix & Retry (secondary), Continue with Warnings (primary) — make primary show a warning confirmation
- Validation: none

F) Export Report
- Purpose: choose format(s) and include audit excerpt toggle
- Inputs: checkboxes JSON/CSV/PDF, toggle include audit log
- Buttons: Export (primary), Cancel
- Expected: triggers file download and shows toast


14. Notifications

Types
- Toast (ephemeral, top-right) for quick feedback: success, info, warning, error
- Persistent notifications (bell icon) for long-running tasks or failures with details

Events triggering notifications
- Upload success/failure
- AI job completion/failure
- Merge/Split/Approve/Reject actions
- Export ready

Design
- Toast auto-dismiss: 4–8 seconds; error toasts have "View details" link to persistent logs
- Notification center lists recent events with link to relevant UX context (ingest or theme)


15. Theme Merge Flow

Purpose
- Combine two or more related themes into a single theme, preserving evidence and audit history.

Steps
1. In Themes list, multi-select checkboxes for 2+ themes (or select theme, open context menu -> "Merge into..." then pick others).
2. Click "Merge" CTA (enabled when >=2 selected).
3. Merge modal opens: select target theme name (pre-filled), optional description and checkbox "Preserve original theme names in audit notes".
4. Confirm Merge.
5. Backend action: start transactional merge: create/choose target theme, reassign member feedback items, recompute deterministic metrics, update time-series, delete or mark source themes as merged (store prior IDs), write audit log entry with full details.
6. UI: show success toast and refresh Themes list showing merged counts.

Edge cases
- Conflicting membership (if same item appears multiple times): de-duplicate members in target theme.
- Concurrent merges: lock involved theme records during operation and show conflict error if lock fails.

Expected results
- Single target theme with union of all distinct items, updated metrics, and an audit entry showing originating themes and user/timestamp.


16. Theme Split Flow

Purpose
- Extract a subset of feedback items from a theme to create a new theme.

Steps
1. Open Theme Detail.
2. Select items in Supporting Feedback list via checkboxes (must be at least 1).
3. Click "Split" action.
4. Split modal: enter new theme name and optional description.
5. Confirm Create.
6. Backend: transactional operation to remove selected items from original theme and create new theme with those items; recompute counts/distributions for both; write audit log.
7. UI: show toast and present the new theme as selected in Themes list.

Edge cases
- Trying to split all items: system should either prevent splitting all items (require original theme to remain non-empty) or allow and mark original as empty and advise renaming; prefer to allow but show warning.

Expected results
- Two themes with correct counts, new theme visible and editable, audit record present.


17. Theme Rename Flow

Purpose
- Edit label for human-readability and alignment with org language.

Steps
1. Click pencil icon next to theme name in Theme Detail or from Themes list context menu -> Rename.
2. Inline edit or modal (small) appears with input prefilled with current name.
3. Enter new name -> Save.
4. Backend: update theme name and write audit record (old name, new name, user, timestamp).
5. UI: update name in all views immediately.

Validation
- Name required, max length (e.g., 200 chars), no leading/trailing whitespace.
- Disallow duplicate theme names within same dataset (show suggested suffix if duplicate).

Expected results
- Theme displays new name; audit stores previous name.


18. Theme Approval Flow

Purpose
- Mark theme as approved for inclusion in final synthesis report.

Steps
1. In Theme Detail, click Approve (primary green CTA).
2. Approve modal: optional note to include in report; Show deterministic metrics summary and count of supporting items.
3. Confirm Approve.
4. Backend: set approved flag, record user/timestamp, persist optional note, and write audit event.
5. UI: theme status changes to Approved; show success toast and include theme in Reports list.

Validation
- Only users with Analyst or Admin role may approve.
- Require at least one supporting feedback item for approval; otherwise block with validation.

Expected results
- Approved theme status shown; included in saved/exported reports.


19. Responsive Design Guidelines

Breakpoints
- Mobile: <= 480px
- Tablet: 481px - 768px
- Desktop: 769px - 1366px
- Wide: >1366px

Layout principles
- Mobile: Single-column stacked layout. Navigation collapses to a hamburger menu. Theme list collapses to a select dropdown above theme detail. Supporting feedback becomes the main content (full width) after selecting a theme.
- Tablet: Two-column layout: Theme list collapses to top or left pane (collapsible). Theme detail and feedback split vertically.
- Desktop: Full three-column layout as previously described.

Component responsiveness
- Tables collapse to cards on small screens: each row becomes a card with primary fields visible and a chevron to reveal details.
- Charts: show simplified versions (no hover tooltips on very small screens) and provide numeric legends.
- Modals: Full-screen at mobile; centered overlay at tablet/desktop.

Touch targets & spacing
- Minimum touch target 44x44 px for interactive elements on mobile.
- Use 8px grid for spacing and layout.


20. UI Components List

Atomic components
- Button (primary, secondary, ghost, danger)
- IconButton
- Input (text, textarea)
- FileUploader (drag-drop + fallback)
- Select / MultiSelect
- Checkbox
- Radio
- Badge / Chip / Status Chip
- Tooltip
- Modal
- Toast / Notification
- Tabs
- Pagination controls
- Skeleton loaders
- Inline editable text

Composite components
- Header / TopNav
- Sidebar (themes list)
- Theme Card (name, status chip, count, sparkline)
- Ingest Row (in Dashboard)
- Feedback Table / Feedback Card
- Deterministic Metrics Card (counts + small charts)
- Time-series Chart (line)
- Distribution Chart (pie or horizontal bar)
- Audit Log List (compact entries)
- Merge/Split Modal

Accessibility & a11y components
- Skip-to-content link
- ARIA-labeled regions
- Keyboard focus outlines

Design tokens (suggested)
- Colors: primary, primary-600, success, danger, warning, neutral-100..900
- Spacing: spacing-1 (4px) base unit, spacing-2 (8px), spacing-3 (12px)
- Border radius: small (4px), medium (8px)
- Typography: H1 (28px), H2 (22px), H3 (18px), Body (14/16px)


Per-page detailed specs (with Inputs, Buttons, Tables, Cards, Charts, Actions, Validation, Expected Results)

A. Dashboard (detailed)
Purpose: Overview and quick access.
Inputs: Search bar, quick filter (AI enabled toggle for Admin)
Buttons: Upload CSV (primary), View Reports, Actions on ingest row (View/Export/Delete)
Tables: Recent ingests table with columns: Ingest Title, Uploaded by, Date, Status, Items, Suggested Themes
Cards: Summary cards: Last ingest items, Suggested themes, Approved, Rejected
Charts: small sparkline per ingest (optional)
Actions: Click ingest -> Ingest Detail; click Upload -> CSV Upload page; click Report -> Report Page
Validation: Search input trimmed; delete requires Admin confirmation
Expected Results: Dashboard lists recent ingests; actions trigger relevant pages

B. CSV Upload Page (detailed)
Purpose: Upload and validate CSV
Inputs: File chooser (drag/drop), Ingest title (optional), Description (optional)
Buttons: Upload & Parse (primary), Cancel
Tables: Preview table showing first 10 rows (Row ID, truncated feedback, source, user type, product area, date, rating)
Cards: Validation issues card listing header and row errors
Actions: Upload -> ingests endpoint -> returns job id; on success redirect to Ingest Detail
Validation: Required headers; date parseable; non-empty feedback text
Expected Results: On success user redirected to Ingest Detail; on validation error show details

C. AI Analysis Progress Page (detailed)
Purpose: Show AI job progress
Inputs: None
Buttons: Cancel Analysis, Retry (on failure)
Tables/Cards: Steps timeline card, small preview card of suggested themes
Charts: Progress bar
Actions: Auto-refresh via polling or websocket
Validation: Show errors with codes; require admin to toggle AI off if needed
Expected Results: On completion offer "Open Suggested Themes"

D. Theme Review Page (detailed)
Purpose: Curate suggested themes
Inputs: Theme search, filters (status/source/user type), feedback text search
Buttons: Rename, Merge, Split, Reject, Approve, Export theme
Tables: Supporting feedback table with columns: Row ID, feedback, source, user type, date, selection checkbox
Cards: Deterministic Metrics card (counts and distributions), AI suggestion card (suggested problem statement + confidence)
Charts: Pie chart (source distribution), Bar chart (user type distribution), Line chart (time series)
Actions: Edit name, Approve (open modal), Merge (open modal), Split (modal), Reject (modal), Add comment to feedback
Validation: Approve requires >=1 member; split requires >=1 selected item; merge requires >=2 themes selected
Expected Results: After actions, counts recalculated and audit logged

E. Report Page (detailed)
Purpose: View and export saved reports
Inputs: Report search and filter, toggle include audit log
Buttons: Export (JSON/CSV/PDF), Save Report
Tables: Approved themes summary table (theme, items, distributions)
Cards: Report metadata card
Charts: small inline charts in the table rows
Actions: Download files, Open theme citations
Validation: Save requires >=1 approved theme
Expected Results: Downloaded file contains required info, report saved in list


Appendix: Copy guidelines & microcopy
- Buttons: Use explicit verbs — "Upload & Parse", "Approve Theme", "Merge themes".
- Labels: "AI suggested" badge for all AI-generated content and confidence score presented as percentage or low/med/high.
- Tooltips: Provide hover help for "Deterministic counts are computed by system code and are authoritative." and "AI suggestions are optional and should be reviewed."
- Error messages: Provide error code and steps: "Error 422: CSV validation failed — 12 rows contain missing dates. Download error report."


Appendix: QA checklist (for handoff)
- CSV parsing tests with sample files including edge cases (missing headers, malformed dates, large files)
- Deterministic counts verification: export numeric results and verify they sum to input rows
- Theme operations: test rename/merge/split/reject/approve flows with audit log checks
- AI job mocking: verify UI handles success/partial success/failure
- Accessibility checks: keyboard navigation for main flows; ARIA labels for dynamic content

---

End of UI / UX specification.
