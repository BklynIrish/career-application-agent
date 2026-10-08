# Database design

The running Phase 1 schema contains only `jobs` and Alembic's migration-version table. The other entities below are the intended design, not implemented tables. Add them through later reviewed migrations.

## Implemented table

| `jobs` column | Type | Meaning |
| --- | --- | --- |
| `id` | varchar(36), primary key | Application-generated UUID |
| `title` | varchar(200), required | Manually supplied posting title |
| `company` | varchar(200), required | Employer name |
| `description` | text, required | Pasted description; API limit 50,000 characters |
| `source_kind` | varchar(40), required | API accepts `pasted` or `daily_feed_manual` |
| `source_url` | varchar(2048), nullable | Validated HTTP/HTTPS reference; no fetching |
| `content_hash` | varchar(64), unique | Normalized company/title/description fingerprint |
| `created_at` | timestamp with time zone, required | UTC intake time |

UUIDs and timestamps are populated by the application. Direct SQL imports must supply them. API validation currently enforces input lengths and source choices; future bulk import migrations should add database-level domain constraints as needed.

## Planned entities and relationships

| Entity | Key fields and relationship | Purpose |
| --- | --- | --- |
| `source_documents` | id, document kind, original filename, SHA-256, immutable storage path, version label, imported_at | Versions of HTCMF and master résumé copies |
| `career_facts` | id, category, structured value, verification_state, verified_at | Curated claims eligible for drafting |
| `fact_sources` | fact_id FK, source_document_id FK, locator, excerpt | Many-to-many evidence lineage |
| `job_requirements` | id, job_id FK, text, category, mandatory flag, extraction version, review_state | Reviewed requirements; preserve extraction versions |
| `assessments` | id, job_id FK, eligibility, score, coverage, policy version, source-set hash, created_at | Historical assessment snapshots |
| `requirement_matches` | assessment_id FK, requirement_id FK, fact_id FK (nullable), match value, rationale | Evidence for each score contribution; multiple facts may support a requirement |
| `application_packets` | id, job_id FK, version, parent_packet_id FK, master_source_id FK, manifest_hash, validation_state | Immutable draft packet versions |
| `packet_artifacts` | id, packet_id FK, kind, path, SHA-256 | Generated résumé/letter/answers bytes |
| `packet_claims` / `claim_facts` | packet_id FK, claim text; claim_id FK + fact_id FK | Inspectable evidence lineage for generated text |
| `approvals` | id, packet_id FK, manifest_hash, approver, approved_at, revoked_at | Approval of exact application contents |
| `applications` | id, job_id FK, packet_id FK, status, submitted_at | Employer-facing application record; draft approval and employer outcome are distinct |
| `application_events` | id, application_id FK, old/new status, timestamp, note | Append-only outcome history |
| `submission_attempts` | id, application_id FK, packet_id FK, approval_id FK, idempotency_key unique, destination, result | Future authorized submission/reconciliation records |
| `audit_events` | id, event type, actor, entity reference, time, metadata | Review and workflow trace without logging unnecessary personal text |

## Planned invariants

- Source path and hash are immutable; a changed file is a new document version.
- Rejected and pending facts never support approved application claims.
- Packet versions and artifact bytes are immutable. Revisions create a new packet.
- Approvals bind to a packet and matching manifest hash; a new packet needs new approval.
- Foreign keys preserve lineage. Use restrictive deletion for evidence/approved packets rather than cascading away history.
- A requirement with no verified match is visibly unsupported; an unreviewed match is visibly unknown.
- Status changes have dated events. Proposed employer statuses: `saved`, `prepared`, `submitted`, `screening`, `interview`, `offer`, `rejected`, `withdrawn`.
- Unknown historic dates remain null with a provenance note. Seed known prior applications/rejections only after verifying the relevant job identity; do not invent exact dates.
- Back up PostgreSQL and private documents together before real application tracking; neither a Git commit nor a Docker volume alone is a complete backup.

This design uses relational joins for evidence and workflow rules. JSON can hold versioned structured model output and score breakdowns later, but authoritative facts and approvals remain explicit records.
