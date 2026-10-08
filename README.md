# Project 5 — AI Career Application Agent

A Python-backed workflow for finding suitable healthcare technology jobs, producing evidence-backed application drafts, and tracking outcomes. The employment workflow is the primary product; the repository is a portfolio demonstration of its engineering.

## Current release: Phase 1

Implemented: paste a job description; save it; detect a duplicate description; list and inspect saved jobs. React calls FastAPI; SQLAlchemy stores records in PostgreSQL; Alembic manages the initial schema. No LLM call, source-document ingestion, fit score, résumé generation, approval action, or submission integration is implemented yet.

Start with [the macOS setup guide](docs/PHASE_1_MACOS.md). See [architecture](docs/ARCHITECTURE.md) and [database design](docs/DATABASE_DESIGN.md).

## Source protections

Original HTCMF and master résumés remain external, untouched source documents. Future ingestion will accept read-only copies, fingerprint them, and create new derived artifacts with unique version identifiers. The `private/` directory and `.env` are excluded from Git. This starter contains no personal career records or API keys.

## Repository structure

- `backend/app/`: API, input/output schemas, database models and sessions.
- `backend/alembic/versions/`: explicit schema migrations.
- `backend/tests/`: API behavior checks using an isolated SQLite database.
- `frontend/src/`: React intake form and saved-job view.
- `compose.yaml`: local PostgreSQL container and persistent named volume.
- `docs/`: architecture, database plan and step-by-step macOS setup.
- `.env.example`: local configuration template; copy to ignored `.env`.
- `private/`: create locally for source copies and derived artifacts; excluded from the repository.

## Development roadmap

1. **Phase 1 — foundation:** get intake working on macOS and confirm PostgreSQL persistence.
2. **Phase 2 — verified evidence:** review current HTCMF/master résumés; ingest copies; curate verified career facts and source citations. Preserve applied/rejected role history to prevent repeat recommendations.
3. **Phase 3 — matching:** extract requirements, review extraction, compute versioned fit scores and route to an appropriate master résumé. Begin with remote healthcare implementation, operations and analytics bridge roles; eligibility and the user's updated preferences govern routing.
4. **Phase 4 — drafting:** generate structured drafts using only verified facts; show claim citations and unsupported requirements; export new résumé and cover-letter versions.
5. **Phase 5 — review and tracking:** approve an exact packet, export for manual application, record submission and subsequent outcomes. Manual submission is the first complete MVP.
6. **Later — integrations:** connect authorized job sources and, only if useful and supported, an application submission adapter with server-enforced approval checks.

Project 6 can reuse general workflow patterns, audit events and adapter boundaries. It should have a separate repository and database; no patient data or healthcare referral functionality belongs in Project 5.

## Local verification

From `backend/`, after activating the virtual environment: `pytest -q`.

From `frontend/`: `npm run build`.

API tests use SQLite to check request validation, persistence within a test, retrieval, duplicate handling and absent submission routes. These tests do not prove PostgreSQL compatibility. The macOS guide includes a PostgreSQL migration and persistence smoke check. See [validation record](docs/VALIDATION.md) for checks actually run on this starter.

## Intended operating boundary

Single-user, localhost development only. Authentication, deployment, backup automation and multi-user isolation are future work. The Vite proxy is a development feature; a deployed frontend will need an explicit API routing configuration. Credentials and personal documents stay outside public Git history. The application treats imported job descriptions as untrusted text, not instructions for an AI model.
