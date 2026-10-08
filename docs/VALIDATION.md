# Phase 1 validation record

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
