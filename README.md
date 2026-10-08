# Project 5 — AI Career Application Agent

A Python-backed workflow for finding suitable healthcare technology jobs, producing evidence-backed application drafts, and tracking outcomes. The employment workflow is the primary product; the repository is a portfolio demonstration of its engineering.

## Current release: Phase 2A — source registry and manual evidence review

Implemented: paste/save/review job descriptions; register separate DOCX/PDF/TXT/MD source copies with SHA-256 and version links; add manual career facts with document or user-confirmation provenance; review them as pending, verified or rejected; inspect review history and stored-file integrity. React calls FastAPI; SQLAlchemy stores records in PostgreSQL; Alembic manages schema revisions. No LLM call, automatic text extraction, fit score, résumé generation, application approval, or submission integration is implemented yet. Fact verification is distinct from approval to submit an application.

Start with [the macOS setup guide](docs/PHASE_1_MACOS.md). See [architecture](docs/ARCHITECTURE.md) and [database design](docs/DATABASE_DESIGN.md).

For an existing Phase 1 installation, use [the Phase 2 update guide](docs/PHASE_2_MACOS.md). For a new installation, Phase 1's environment/startup commands still apply; `upgrade head` now creates all four application tables, health reports phase 2, and the full test suite has 15 tests.

## Source protections

Original HTCMF and master résumés remain external, untouched source documents. Upload creates a new, read-only private copy under a UUID filename. The API does not offer source overwrite or deletion. New versions are new records; pending facts must be reviewed. The `private/` directory and `.env` are excluded from Git. The code and demo fixtures contain no personal career records or API keys.

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
2. **Phase 2 — verified evidence:** source registration and manual fact review implemented; next add extraction with reviewed candidates and richer evidence linking. Preserve applied/rejected role history to prevent repeat recommendations.
3. **Phase 3 — matching:** extract requirements, review extraction, compute versioned fit scores and route to an appropriate master résumé. Begin with remote healthcare implementation, operations and analytics bridge roles; eligibility and the user's updated preferences govern routing.
4. **Phase 4 — drafting:** generate structured drafts using only verified facts; show claim citations and unsupported requirements; export new résumé and cover-letter versions.
5. **Phase 5 — review and tracking:** approve an exact packet, export for manual application, record submission and subsequent outcomes. Manual submission is the first complete MVP.
6. **Later — integrations:** connect authorized job sources and, only if useful and supported, an application submission adapter with server-enforced approval checks.

Project 6 can reuse general workflow patterns, audit events and adapter boundaries. It should have a separate repository and database; no patient data or healthcare referral functionality belongs in Project 5.

## Local verification

From `backend/`, after activating the virtual environment: `pytest -q`.

From `frontend/`: `npm run build`.

API tests use SQLite to check jobs, source storage, review history, stale-review conflicts, rejected evidence, and migration preservation of existing jobs. These tests do not prove PostgreSQL compatibility. The macOS guides include PostgreSQL migration and persistence smoke checks. See [validation record](docs/VALIDATION.md) for checks actually run.

## Intended operating boundary

Single-user, localhost development only. Authentication, deployment, backup automation and multi-user isolation are future work. The Vite proxy is a development feature; a deployed frontend will need an explicit API routing configuration. Credentials and personal documents stay outside public Git history. The application treats imported job descriptions as untrusted text, not instructions for an AI model.
