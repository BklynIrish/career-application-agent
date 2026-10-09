# Fact correction update

This patch is for a project with the bulk evidence update already applied. Leave existing career facts and source files unchanged while installing. It adds a prefilled Correct this fact form and migration 0003, which creates a link table without altering existing fact, review, job or source records. No new package dependencies or LLM key are needed.

## Apply

Extract Project_5_Fact_Corrections_Update.zip into Downloads. Use an available VS Code terminal; no need to discard or commit the existing bulk feature first.

```bash
cd ~/Projects/career-application-agent
git branch --show-current
git apply --check ~/Downloads/Project_5_Fact_Corrections_Update/fact-corrections.patch
git apply ~/Downloads/Project_5_Fact_Corrections_Update/fact-corrections.patch
cd backend
source .venv/bin/activate
python -c 'from dotenv import load_dotenv; load_dotenv("../.env"); from alembic.config import main; main(argv=["upgrade", "head"])'
python -c 'from dotenv import load_dotenv; load_dotenv("../.env"); from alembic.config import main; main(argv=["current"])'
pytest -q
```

Expect 0003 (head) and 27 tests passed. If patch validation fails, stop and share the error. Do not force it. Apply on phase-2-bulk-evidence, or your current branch containing that feature; this does not require a branch switch.

## Restart

In the backend server terminal, Ctrl+C, then:

```bash
cd ~/Projects/career-application-agent/backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file ../.env
```

In an available terminal:

```bash
cd ~/Projects/career-application-agent/frontend
npm run build
```

In the React terminal, Ctrl+C and run npm run dev from frontend. Open http://127.0.0.1:8000/ready to confirm readiness, then refresh http://127.0.0.1:5173/.

## Use

Under Review career facts, open Correct this fact on a fact without a replacement. Statement and category are prefilled. Change wording, scope or category; enter a reason; click Save corrected Pending version. The original statement and source excerpt remain unchanged. The old record is Rejected with a supersession note, the replacement is Pending, and both are linked with the reason. This operation commits all changes together or rolls them all back.

Select All to see both versions. The old card shows the replacement ID; the new card shows its original ID and correction reason. Superseded entries cannot be verified or returned to Pending. Further corrections are made on the latest replacement, forming a chain. Correcting a category alone is supported and does not require retyping the statement or source.

Do not add invented details. Changing a statement does not make its original excerpt support the revision; reviewers must assess that difference. The correction reason records why it changed, not independent evidence. If you need a different source, add a new fact explicitly linked to that source instead.

For clarification only, use Review this fact and a review note. Keep uncertain claims Pending. Nothing is automatically verified. Original master documents are never changed by corrections.

## First Mac check

Use an existing rejected synthetic test fact without a correction link. Correct its wording to explicitly identify it as a correction test and change category if useful. Save, confirm old version remains Rejected, new version is Pending and links display. Reject the replacement as test-only through the review form. Check both review histories and refresh to confirm persistence. Existing real facts and documents should remain unchanged.

Then correct the misclassified requirements/planning or SQL/Python experience facts using a category-only correction. Select Experience, give the reason, save the Pending replacement and review its accuracy separately. Keep disputed financial or percentage claims Pending until their meaning and scope are confirmed.

## Validation and commit

Automated tests exercise unchanged evidence, category-only corrections, correction chains, stale revisions, prevention of reviving superseded records, duplicate conflicts, source integrity, rollback after database failure, and migration retention of existing facts/reviews/jobs. Local tests use SQLite; PostgreSQL and browser workflow require your Mac checks.

After successful Mac validation, stage both bulk and correction changes, inspect staged paths (no private documents or .env), then commit and push phase-2-bulk-evidence. If bulk changes were already committed, only the correction changes will be staged. Record actual validation in the PR.
