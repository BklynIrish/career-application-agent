import React, { useEffect, useState } from 'react';
import BulkEvidencePanel from './BulkEvidencePanel';
import CorrectionForm from './CorrectionForm';

const kinds = { htcmf: 'HTCMF', master_resume: 'Master résumé', supporting: 'Supporting document' };
const bases = { user_confirmed: 'User-confirmed', document_supported: 'Document-supported', independently_documented: 'Independently documented' };

function FactCard({ fact, sources, corrections, request, refresh }) {
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState(null);
  const [decision, setDecision] = useState('verified');
  async function review(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.expected_revision = fact.revision;
    if (data.decision !== 'verified') data.verification_basis = null;
    setBusy(true); setMessage('');
    try {
      await request(`/facts/${fact.id}/reviews`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      form.reset();
      setHistory(await request(`/facts/${fact.id}/reviews`));
      await refresh();
      setMessage('Review recorded.');
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  async function showHistory() {
    try { setHistory(await request(`/facts/${fact.id}/reviews`)); }
    catch (error) { setMessage(error.message); }
  }
  const source = sources.find(item => item.id === fact.source_document_id);
  const outgoing = corrections.find(item => item.original_fact_id === fact.id);
  const incoming = corrections.find(item => item.replacement_fact_id === fact.id);
  return <article>
    {outgoing && <p><strong>Superseded.</strong> Replacement ID: {outgoing.replacement_fact_id}. Select All or Pending to find the replacement.</p>}
    {incoming && <p><strong>Corrected version.</strong> Original ID: {incoming.original_fact_id}<br />Reason: {incoming.reason}</p>}
    <p className={`badge ${fact.status}`}>{fact.status.toUpperCase()} · {fact.category}</p>
    <h3>{fact.statement}</h3>
    <p>{fact.provenance_kind === 'document' ? `Source: ${source?.original_filename || fact.source_document_id}` : 'Source: user confirmation'}</p>
    <p><strong>Locator:</strong> {fact.source_locator}</p>
    <p className="description"><strong>Evidence:</strong> {fact.evidence_note}</p>
    {!outgoing && <CorrectionForm fact={fact} request={request} refresh={refresh} />}
    {!outgoing && <details><summary>Review this fact</summary>
      <p>Verification records your assessment. It does not independently establish that the claim is true. To correct the statement, reject it and create a new fact.</p>
      <form onSubmit={review}>
        <label>Decision<select name="decision" value={decision} onChange={event => setDecision(event.target.value)}>
          <option value="verified">Verify</option><option value="rejected">Reject</option><option value="pending">Return to pending</option>
        </select></label>
        {decision === 'verified' && <label>Verification basis<select name="verification_basis" defaultValue="user_confirmed">
          {Object.entries(bases).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>}
        <label>Review note<textarea name="note" required minLength={5} maxLength={5000} rows={3} placeholder="What you checked or confirmed, and any limitations" /></label>
        <button disabled={busy}>{busy ? 'Saving…' : 'Record review'}</button>
      </form>
    </details>}
    <button type="button" className="secondary" onClick={showHistory}>View review history</button>
    {history && <div>{history.length === 0 ? <p>No reviews yet.</p> : history.map(item => <p key={item.id} className="description">
      {item.previous_status} → {item.decision}{item.verification_basis ? ` · ${bases[item.verification_basis]}` : ''}<br />
      {new Date(item.created_at).toLocaleString()} · {item.actor}<br />{item.note}
    </p>)}</div>}
    <p role="status" aria-live="polite">{message}</p>
  </article>;
}

export default function EvidencePanel({ request }) {
  const [sources, setSources] = useState([]);
  const [facts, setFacts] = useState([]);
  const [corrections, setCorrections] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [provenance, setProvenance] = useState('document');
  const [kind, setKind] = useState('htcmf');
  const [filter, setFilter] = useState('all');
  async function refresh() {
    async function all(path) {
      const rows = [];
      for (let offset = 0; ; offset += 100) {
        const page = await request(`${path}?limit=100&offset=${offset}`);
        rows.push(...page);
        if (page.length < 100) return rows;
      }
    }
    const [documents, evidence, links] = await Promise.all([all('/sources'), all('/facts'), all('/fact-corrections')]);
    setSources(documents); setFacts(evidence); setCorrections(links);
  }
  useEffect(() => { refresh().catch(error => setMessage(error.message)); }, []);
  async function upload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = new FormData(form);
    if (!payload.get('supersedes_id')) payload.delete('supersedes_id');
    setBusy(true); setMessage('');
    try {
      await request('/sources', { method: 'POST', body: payload });
      form.reset(); setKind('htcmf');
      await refresh();
      setMessage('Source copy registered. No facts were automatically extracted or verified.');
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  async function addFact(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    if (!data.source_document_id) data.source_document_id = null;
    setBusy(true); setMessage('');
    try {
      await request('/facts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
      form.reset();
      await refresh();
      setMessage('Fact added as pending. Review it below before verification.');
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  async function checkIntegrity(id) {
    try { await request(`/sources/${id}/integrity`); setMessage('Source copy is intact: its hash matches registration.'); }
    catch (error) { setMessage(error.message); }
  }
  return <>
    <section><h2>Register a source document</h2>
      <p>Upload a separate local copy. Originals remain unchanged. DOCX, PDF, UTF-8 TXT and MD; up to 10 MiB. This step registers bytes, not verified qualifications.</p>
      <form onSubmit={upload}>
        <label>Document<input name="file" type="file" accept=".docx,.pdf,.txt,.md" required /></label>
        <label>Document kind<select name="document_kind" value={kind} onChange={event => setKind(event.target.value)}>
          {Object.entries(kinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label>Version label<input name="version_label" required maxLength={100} placeholder="For example: Working edition · 2026-10-08" /></label>
        <label>Previous version (optional)<select name="supersedes_id" key={kind} defaultValue="">
          <option value="">First version / no previous version</option>
          {sources.filter(source => source.document_kind === kind).map(source => <option key={source.id} value={source.id}>{source.original_filename} · {source.version_label}</option>)}
        </select></label>
        <button disabled={busy}>{busy ? 'Saving…' : 'Register source copy'}</button>
      </form>
      <p role="status" aria-live="polite">{message}</p>
      <h3>Registered sources</h3><p>Registered source versions.</p>
      {sources.length === 0 && <p>No source documents registered yet.</p>}
      {sources.map(source => <article key={source.id}>
        <h3>{source.original_filename}</h3>
        <p>{kinds[source.document_kind]} · {source.version_label} · {source.size_bytes.toLocaleString()} bytes</p>
        <p className="hash">SHA-256: {source.sha256}</p>
        {source.supersedes_id && <p>Previous version ID: {source.supersedes_id}</p>}
        <button className="secondary" type="button" onClick={() => checkIntegrity(source.id)}>Check stored copy integrity</button>
      </article>)}
    </section>
    <BulkEvidencePanel sources={sources} facts={facts} request={request} refresh={refresh} />
    <section><h2>Add a career fact</h2><p>Record one specific claim at a time. Every new fact starts pending.</p>
      <form onSubmit={addFact}>
        <label>Statement<textarea name="statement" required minLength={5} maxLength={5000} rows={3} /></label>
        <label>Category<select name="category">{['experience', 'metric', 'education', 'skill', 'project', 'other'].map(value => <option key={value}>{value}</option>)}</select></label>
        <label>Evidence source<select name="provenance_kind" value={provenance} onChange={event => setProvenance(event.target.value)}>
          <option value="document">Registered document</option><option value="user_confirmation">My confirmation</option>
        </select></label>
        {provenance === 'document' && <label>Source document<select name="source_document_id" required defaultValue="">
          <option value="" disabled>Choose a registered source</option>
          {sources.map(source => <option key={source.id} value={source.id}>{source.original_filename} · {source.version_label}</option>)}
        </select></label>}
        <label>Evidence location<input name="source_locator" required maxLength={500} placeholder="Page/section, or confirmation date and conversation" /></label>
        <label>Supporting excerpt or confirmation<textarea name="evidence_note" required minLength={5} maxLength={5000} rows={3} /></label>
        <button disabled={busy}>{busy ? 'Saving…' : 'Add pending fact'}</button>
      </form>
    </section>
    <section><h2>Review career facts</h2><p>Saved career facts. Review history distinguishes confirmation from documentary support.</p>
      <label>Filter<select value={filter} onChange={event => setFilter(event.target.value)}>{['all', 'pending', 'verified', 'rejected'].map(value => <option key={value}>{value}</option>)}</select></label>
      {facts.filter(fact => filter === 'all' || fact.status === filter).map(fact => <FactCard key={fact.id} fact={fact} sources={sources} corrections={corrections} request={request} refresh={refresh} />)}
      {facts.filter(fact => filter === 'all' || fact.status === filter).length === 0 && <p>No facts in this view yet.</p>}
    </section>
  </>;
}
