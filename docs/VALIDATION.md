# Phase 1 validation record

## Phase 2A validation — October 8, 2026

- 15 tests passed using isolated SQLite databases and temporary private source directories.
- Checks cover source byte/hash integrity, read-only copies, duplicate uploads, version preservation, invalid uploads, pending facts, source validation, review basis/history, stale-review conflicts, rejected evidence, changed/missing sources, cleanup after failed DB commit, and migration preservation of Phase 1 jobs.
- React/Vite production build passed (24 modules).
- PostgreSQL/Docker and browser workflow were not run in the build environment. Follow `PHASE_2_MACOS.md` on the Mac for acceptance checks.
- The known upstream Starlette TestClient deprecation warning remains nonblocking.
- No real career documents were imported and no career claims were marked verified in a live application database by the build.

The historical Phase 1 record follows.

Build date: October 4, 2026 (America/New_York). Build environment: Linux, Python 3.12.14, Node 24.19.0.

| Check | Result | Scope |
| --- | --- | --- |
| `pytest -q` | 5 passed | Isolated SQLite-backed API checks: intake/retrieval, duplicates, invalid inputs, pagination/missing record, absent submission endpoint |
| `npm run build` | Passed | React/Vite bundle compiled successfully |
| Alembic upgrade and current revision | Passed; `0001 (head)` | Temporary SQLite database; confirms migration execution, not PostgreSQL operation |
| PostgreSQL/Docker end-to-end | Not run | Docker is unavailable in this environment; macOS guide gives readiness/persistence acceptance checks |
| macOS installation and browser workflow | Not run | Must be performed on the user's Mac |
| LLM, evidence validation, scoring, approvals, export | Not implemented | Planned later phases |

The test run emitted one upstream deprecation warning about Starlette's httpx TestClient integration. It did not fail the tests. Revisit the test-client dependency when upgrading the backend stack.

`backend/requirements.lock.txt` records exact installed Python package versions, without the local editable package path. `frontend/package-lock.json` records npm package resolution. No original source documents, personal employment claims or API keys were used in validation.

## Phase 2B bulk evidence

22 backend tests passed in the build environment. New checks cover read-only preview, edited statements retaining immutable source excerpts, exact duplicates across attestation/document evidence, possible-overlap flags, invalid import atomicity, DOCX table paragraphs, missing/changed source integrity, PDF extraction rejection, separate batch review histories and stale revision rollback. React production build passed. PostgreSQL and browser checks for this update remain to be performed on the user's Mac. No real career fact was imported into a live database by these tests.

## Fact correction update

27 backend tests passed in the build environment; React production build passed. Corrections retain original source evidence and review history, create linked Pending replacements, support category-only changes and correction chains, block stale updates and reactivation of superseded facts, and roll back after commit failures. Migration 0003 preserves existing jobs, facts and reviews. PostgreSQL and correction-form browser validation remain to be completed on the user's Mac.
