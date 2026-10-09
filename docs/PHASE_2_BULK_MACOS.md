# Phase 2B: bulk evidence intake

This update adds local DOCX/TXT/MD passage extraction, editable candidate selection, duplicate detection and transactional batch reviews. No new dependencies, database migrations or LLM API key are required. PDF extraction, OCR, automatic fact interpretation and résumé generation are not included. DOCX body paragraphs and table-cell paragraphs are read; headers, footers, comments and embedded images are not extracted. A paragraph can contain several claims: edit to one accurate, scoped statement or leave it unselected. Keep the full attached source excerpt for comparison.

## 1. Apply the update

Extract `Project_5_Phase_2_Bulk_Update.zip` in Downloads. The extracted folder should contain `bulk-evidence.patch` and this guide. Do not replace your project directory.

Use an available VS Code terminal; leave the API and React terminals open.

```bash
cd ~/Projects/career-application-agent
git status --short
git branch --show-current
```

Working tree should be clean and branch should be `phase-2-bulk-evidence`. If you have not created it yet, run `git switch -c phase-2-bulk-evidence` from updated `main`. Do not run that command again if the branch already exists.

```bash
git apply --check ~/Downloads/Project_5_Phase_2_Bulk_Update/bulk-evidence.patch
git apply ~/Downloads/Project_5_Phase_2_Bulk_Update/bulk-evidence.patch
cd backend
source .venv/bin/activate
pytest -q
```

Expect 22 tests to pass. The existing Starlette/httpx deprecation warning may remain. If patch validation fails, stop and share the error instead of forcing it.

## 2. Restart and build

In the API terminal, press Ctrl+C, then:

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

In the React terminal, restart with Ctrl+C, then `npm run dev`. Refresh http://127.0.0.1:5173/ and open Sources & evidence. Existing source copies, facts, reviews and jobs should remain. Stored filenames must exactly match database storage_filename values; identify documents using displayed original names and labels, not renaming private copies.

## 3. Test on synthetic evidence first

Choose synthetic_source.md in the new Bulk evidence import & review section. Click Preview candidate facts. Nothing should be selected by default. Headings and notes may be offered alongside claims; extraction is not a truth assessment. The already-rejected synthetic statement should be flagged as an exact duplicate. Select only that unchanged statement and click Save selected as Pending. Expect zero created and one duplicate skipped, leaving its rejection and review history unchanged.

To exercise batch review, use an existing pending synthetic fact, or select another synthetic passage clearly labeled as test data. Save it as Pending. Select the pending test fact, choose Reject, enter a test-only rejection note, check the explicit review acknowledgment, then Record reviews. Check the individual history below. Do not verify test data for real applications.

## 4. Import real claims

Choose one registered résumé and preview it. Expand Compare existing facts before selecting anything. Your two existing user-confirmed metrics stay unchanged. Skip passages repeating those claims, even when phrased differently. Exact duplicate detection normalizes case, whitespace and punctuation. Similarity flags are heuristic and can miss equivalent claims or flag unrelated ones; they do not establish equivalence or truth.

Select only accurate, specific career claims. Edit statements to preserve dates, employer, scope and approximate quantities; do not add qualifications missing from the source or your confirmation. Choose a category for each. Save selected as Pending. The server retains the original excerpt and its DOCX paragraph or text-line locator separately from your edited statement.

Review selected pending facts with their displayed source and excerpt. Use one batch only when the same verification basis and note accurately apply to every selected fact. User-confirmed records your own confirmation. Document-supported records textual support, not independent substantiation. Independently documented requires actual independent evidence; a self-authored résumé does not qualify. Use individual reviews when explanations differ.

A stale revision, missing source, changed source or other review error rolls back the entire review batch. Refresh and reassess before retrying. Correct an already-saved statement by rejecting it and adding a new fact; the source copies and old reviews remain unchanged.

## 5. Commit after Mac checks pass

```bash
cd ~/Projects/career-application-agent
git add backend frontend docs
git --no-pager diff --cached --name-only
git status --short
```

Stage only code and documentation. No private documents, .env, virtual environments, node_modules or dist should appear. Then:

```bash
git commit -m "Add bulk source extraction and evidence reviews"
git push -u origin phase-2-bulk-evidence
```

Create a PR targeting main and record your actual Mac validation. No application submission is enabled. This remains a local single-user workflow; exact duplicate prevention is designed for serial local imports, without a new database uniqueness constraint for simultaneous imports.
