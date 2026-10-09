import React, { useState } from 'react';

const categories = ['experience', 'metric', 'education', 'skill', 'project', 'other'];

export default function BulkEvidencePanel({ sources, facts, request, refresh }) {
  const [sourceId, setSourceId] = useState('');
  const [preview, setPreview] = useState(null);
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [decision, setDecision] = useState('verified');
  const [basis, setBasis] = useState('user_confirmed');
  const [note, setNote] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const pending = facts.filter(fact => fact.status === 'pending');
  const selectedFacts = pending.filter(fact => selected.includes(fact.id));
  async function run(action) {
    setBusy(true); setMessage('');
    try { await action(); } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  async function extract() {
    await run(async () => {
      const result = await request(`/sources/${sourceId}/candidates`);
      setPreview({ ...result, candidates: result.candidates.map(item => ({ ...item, chosen: false, category: 'other' })) });
      setMessage(`${result.candidates.length} source passages found. Select only specific career claims; omit headings, contact details and unsupported statements.`);
    });
  }
  function edit(index, changes) {
    setPreview(current => ({ ...current, candidates: current.candidates.map((item, i) => i === index ? { ...item, ...changes } : item) }));
  }
  async function saveCandidates() {
    await run(async () => {
      const items = preview.candidates.filter(item => item.chosen).map(({ candidate_id, statement, category }) => ({ candidate_id, statement, category }));
      const result = await request(`/sources/${preview.source_id}/facts/import`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_sha256: preview.source_sha256, items }) });
      setPreview(null); await refresh();
      setMessage(`${result.created} pending facts saved; ${result.skipped_duplicates} exact duplicates skipped. Nothing was verified automatically.`);
    });
  }
  async function review(event) {
    event.preventDefault();
    await run(async () => {
      const result = await request('/facts/bulk-reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        decision, verification_basis: decision === 'verified' ? basis : null, note,
        items: selectedFacts.map(fact => ({ fact_id: fact.id, expected_revision: fact.revision }))
      }) });
      setSelected([]); setConfirmed(false); setNote(''); await refresh();
      setMessage(`${result.reviewed} individual reviews recorded: ${result.decision}.`);
    });
  }
  return <section><h2>Bulk evidence import & review</h2>
    <p>Extract source passages locally from DOCX, TXT or MD. No LLM key is needed. PDF extraction and scanned documents are not supported yet. Uploading a résumé does not prove its claims.</p>
    <label>Source to extract<select value={sourceId} disabled={busy} onChange={event => { setSourceId(event.target.value); setPreview(null); }}>
      <option value="">Choose a registered source</option>
      {sources.map(source => <option key={source.id} value={source.id}>{source.original_filename} · {source.version_label}</option>)}
    </select></label>
    <button type="button" disabled={busy || !sourceId} onClick={extract}>Preview candidate facts</button>
    <p role="status" aria-live="polite">{busy ? 'Working…' : message}</p>
    {preview && <div>
      <p>Nothing is selected by default. Edit each statement to keep one accurate claim and its scope. The original source excerpt remains attached. Exact duplicates are skipped at save; differently worded claims require your comparison.</p>
      <details><summary>Compare existing facts ({facts.length})</summary>{facts.map(fact => <p key={fact.id}>{fact.status}: {fact.statement}</p>)}</details>
      {preview.candidates.map((item, index) => <article key={item.candidate_id}>
        <label className="check-label"><input type="checkbox" checked={item.chosen} disabled={busy} onChange={event => edit(index, { chosen: event.target.checked })} /> Import this passage as a pending fact</label>
        <p><strong>{item.source_locator}</strong></p><p className="description">Source excerpt: {item.evidence_note}</p>
        {item.duplicate_fact_id && <p>An existing fact has the same statement. Unless you edit the statement, it will be skipped.</p>}
        {item.possible_matches.length > 0 && <div><strong>Possible overlap — compare before selecting:</strong>{item.possible_matches.map(fact => <p key={fact.id}>{fact.status}: {fact.statement}</p>)}</div>}
        <label>Candidate statement<textarea value={item.statement} disabled={busy} minLength={5} maxLength={5000} onChange={event => edit(index, { statement: event.target.value })} /></label>
        <label>Category<select value={item.category} disabled={busy} onChange={event => edit(index, { category: event.target.value })}>{categories.map(value => <option key={value}>{value}</option>)}</select></label>
      </article>)}
      <button type="button" disabled={busy || !preview.candidates.some(item => item.chosen) || preview.candidates.some(item => item.chosen && item.statement.trim().length < 5)} onClick={saveCandidates}>Save selected as Pending</button>
    </div>}
    <h3>Review selected pending facts</h3>
    <p>Choose up to 200 facts you have checked. The same basis and note will be recorded separately for every selected fact. Use individual reviews for claims needing different explanations.</p>
    {pending.length === 0 && <p>No pending facts.</p>}
    {pending.map(fact => <article key={fact.id}><label className="check-label"><input type="checkbox" checked={selected.includes(fact.id)} disabled={busy} onChange={event => { setConfirmed(false); setSelected(current => event.target.checked ? [...current, fact.id] : current.filter(id => id !== fact.id)); }} /> {fact.statement} — {fact.source_locator}</label><p>Source: {sources.find(source => source.id === fact.source_document_id)?.original_filename || "My confirmation"}</p><p className="description">Evidence: {fact.evidence_note}</p></article>)}
    {selectedFacts.length > 0 && <form onSubmit={review}>
      <p>{selectedFacts.length} facts selected.</p>
      <label>Decision<select value={decision} disabled={busy} onChange={event => { setDecision(event.target.value); setConfirmed(false); }}><option value="verified">Verify</option><option value="rejected">Reject</option></select></label>
      {decision === 'verified' && <label>Verification basis<select value={basis} disabled={busy} onChange={event => { setBasis(event.target.value); setConfirmed(false); }}><option value="user_confirmed">User-confirmed</option><option value="document_supported">Document-supported</option><option value="independently_documented">Independently documented</option></select></label>}
      <p>Document-supported means the passage supports the wording. A self-authored résumé is not independent verification.</p>
      <label>Shared review note<textarea value={note} required minLength={5} maxLength={5000} disabled={busy} onChange={event => { setNote(event.target.value); setConfirmed(false); }} /></label>
      <label className="check-label"><input type="checkbox" required checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} /> I reviewed every selected claim, including its source, scope and verification basis.</label>
      <button disabled={busy || !confirmed || selectedFacts.length > 200}>Record {selectedFacts.length} reviews</button>
    </form>}
  </section>;
}
