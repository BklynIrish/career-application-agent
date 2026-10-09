import React, { useState } from 'react';

export default function CorrectionForm({ fact, request, refresh }) {
  const [statement, setStatement] = useState(fact.statement);
  const [category, setCategory] = useState(fact.category);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function correct(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try {
      await request(`/facts/${fact.id}/corrections`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ statement, category, reason, expected_revision: fact.revision }) });
      await refresh();
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  return <details><summary>Correct this fact</summary>
    <p>Revise the statement or category. Saving creates a linked Pending replacement and marks this version Rejected. Its original evidence and all reviews are preserved. The replacement must be reviewed separately.</p>
    <p>Keep new details within what you can support or confirm. If the correction relies on a different source, use Add a career fact instead.</p>
    <form onSubmit={correct}>
      <label>Corrected statement<textarea value={statement} required minLength={5} maxLength={5000} disabled={busy} onChange={event => setStatement(event.target.value)} /></label>
      <label>Corrected category<select value={category} disabled={busy} onChange={event => setCategory(event.target.value)}>{['experience', 'metric', 'education', 'skill', 'project', 'other'].map(value => <option key={value}>{value}</option>)}</select></label>
      <label>Reason for correction<textarea value={reason} required minLength={5} maxLength={4000} disabled={busy} placeholder="For example: corrected category; clarified responsibility; removed an unsupported estimate" onChange={event => setReason(event.target.value)} /></label>
      <button disabled={busy || (statement === fact.statement && category === fact.category)}>{busy ? 'Saving…' : 'Save corrected Pending version'}</button>
    </form><p role="status">{message}</p>
  </details>;
}
