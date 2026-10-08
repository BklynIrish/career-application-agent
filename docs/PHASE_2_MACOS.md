# Phase 2A — install source upload and manual fact review

This increment adds a Sources & evidence workspace to the running application. It preserves the original source documents and the existing jobs table. No LLM account/key is required.

## 1. Stop the development servers

Press Ctrl+C in the FastAPI terminal and the React/Vite terminal. Leave Docker Desktop and PostgreSQL running. Use the third VS Code terminal for the update.

## 2. Apply the update patch

Download `Project_5_Phase_2_Update.zip` and extract it with Finder into Downloads. It contains a `Project_5_Phase_2_Update` directory holding `phase2.patch`, this guide, and `synthetic_source.md`.

The following assumes you extracted it directly into `~/Downloads/`. If the folder is elsewhere, substitute its actual path. Do not unzip it over the existing project or create another project copy.

```bash
cd ~/Projects/career-application-agent
git branch --show-current
git status --short
```

Expect branch `phase-2-verified-evidence` and no status output. If you have uncommitted changes, stop and preserve/review them before applying this patch. If you are still on `main`, switch to the existing Phase 2 branch with `git switch phase-2-verified-evidence`.

Check whether the patch applies cleanly:

```bash
git apply --check ~/Downloads/Project_5_Phase_2_Update/phase2.patch
```

No output means the check passed. Then apply it:

```bash
git apply ~/Downloads/Project_5_Phase_2_Update/phase2.patch
git diff --stat
git status --short
```

The patch changes only code, dependency metadata and documentation. It does not contain `.env`, private career files, PostgreSQL volume files or Git history. `git apply` leaves changes available for inspection on your branch; it does not commit or push. If it reports an error, paste that error and do not use force/reject options.

## 3. Install the new dependency and apply migration 0002

From the project root:

```bash
cd backend
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c 'from dotenv import load_dotenv; load_dotenv("../.env"); from alembic.config import main; main(argv=["upgrade", "head"])'
python -c 'from dotenv import load_dotenv; load_dotenv("../.env"); from alembic.config import main; main(argv=["current"])'
pytest -q
```

Expect `0002 (head)` and **15 passed**. The known test-client deprecation warning can remain. Migration 0002 adds `source_documents`, `career_facts`, and `fact_reviews`; it does not alter or clear `jobs`. Tests use temporary SQLite databases/private test directories and do not import your real documents.

New dependency: `python-multipart` supports the file upload form. The lock records tested package versions; the editable install above keeps the compatible versions already installed on your Mac where possible. No Node/npm upgrade is required.

## 4. Restart both servers

Terminal A, in `backend/` with `.venv` active:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file ../.env
```

Visit [readiness](http://127.0.0.1:8000/ready): expect `{"status":"ready"}`. Health now reports phase 2 and `submission_enabled: false`.

Terminal B:

```bash
cd ~/Projects/career-application-agent/frontend
npm run dev
```

The frontend has no new npm dependency. Open [the app](http://127.0.0.1:5173). Click **Sources & evidence**. Your previously saved job remains in the **Jobs** workspace.

## 5. Test a synthetic source before uploading career documents

In **Register a source document**:

- File: select `synthetic_source.md` from the extracted update directory.
- Kind: Supporting document.
- Version label: `Synthetic test v1`.
- Previous version: leave blank.

Click **Register source copy**. The registry should show filename, kind, version, byte count and SHA-256. Click **Check stored copy integrity**; expect an intact-copy message.

Try uploading that same file again: expect a duplicate-document message and one record. The application rejects identical bytes even if the filename or version label changes. A revised file with different bytes creates a new source version; choose the prior version explicitly when appropriate.

## 6. Add and review a synthetic fact

In **Add a career fact**:

- Statement: `Completed twenty synthetic example initiatives.`
- Category: metric.
- Evidence source: Registered document.
- Source document: choose `synthetic_source.md`.
- Evidence location: `Example claim section`.
- Supporting excerpt: `Completed twenty synthetic example initiatives.`

Click **Add pending fact**. It appears under **Review career facts** with status pending. Open **Review this fact**:

- Decision: Verify.
- Basis: Document-supported.
- Review note: `Synthetic test only; checked the example statement against the source.`

Click **Record review**. Expect verified status. Click **View review history** to see the decision, basis, timestamp and note.

Then reject this synthetic fact with note `Synthetic test only; exclude from real application evidence.` Its history remains, and its current status becomes rejected. This prevents confusing test evidence with real career facts later. A verified status means a human reviewed it; it does not establish truth by itself.

## 7. Register real source copies and add confirmed facts

Use the file picker to choose your current local HTCMF or master résumé. The browser sends bytes to the local API, which saves a separate UUID-named copy in `private/sources/`. It does not modify or move the file you selected. Supported file formats: DOCX, PDF, UTF-8 TXT and MD, up to 10 MiB.

Upload each candidate document with an honest version label, such as `September 15 draft`. A source can be a draft; do not label it finalized unless that is established. Selecting a source registers it but does not extract or verify its contents.

For a fact confirmed directly by you, choose **My confirmation** instead of a document. Enter its specific statement, confirmation date/conversation in Evidence location, and your explicit attestation in Supporting excerpt or confirmation. It starts pending. Review it with basis **User-confirmed** and a note describing what you confirmed. Documentary support and independent documentation use separate review bases.

Record one claim per fact. Preserve scope, dates, qualifiers and whether a monetary amount refers to a directly managed portfolio or a broader program environment. If a claim changes, reject the old fact and add a corrected fact. There is no statement-edit endpoint in this increment, so review history cannot silently shift onto rewritten content.

Automatic document text extraction, many-to-many evidence links, fit scoring and generation are not implemented here. This manual path provides a usable evidence catalog first. Uploaded documents stay local; there are no LLM calls.

## 8. Check persistence and commit after validation

Refresh the app, restart FastAPI and refresh again. Registry and fact history should remain. Your original demo job should still appear in Jobs.

Terminal C:

```bash
cd ~/Projects/career-application-agent/frontend
npm run build
cd ..
git check-ignore .env private/sources/example.docx
git add README.md backend frontend docs
git diff --cached --stat
git status --short
```

Inspect the staged filenames: no `.env`, private documents, virtual environments or installed dependencies. Then:

```bash
git commit -m "Add private source registry and reviewed career evidence"
git push -u origin phase-2-verified-evidence
```

This publishes the code branch while keeping `main` unchanged. It does not publish uploaded career documents or database contents. Authentication is not implemented; keep the service bound to localhost. `local_user` in the review history is a local-session label, not an authenticated identity.

## Validation and limits

Build-environment checks: 13 SQLite-backed tests passed; frontend production build passed; tests include upgrading from 0001 while retaining an existing job. Docker/PostgreSQL and the browser flow still need the Mac checks above. The 10 MiB limit is checked after multipart parsing; this localhost service is not hardened for public upload traffic. Format checks are basic validation, not malware scanning. API-managed copies are read-only and have no overwrite route, but their owner can still change filesystem permissions outside the app; hash checks detect changed bytes.

Back up both PostgreSQL and `private/sources/` before relying on this catalog. Git does not back up ignored private files or the database. No existing master résumé or HTCMF was modified by this update.

## References

- [FastAPI file/form uploads](https://fastapi.tiangolo.com/tutorial/request-forms-and-files/)
- [SQLAlchemy constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
