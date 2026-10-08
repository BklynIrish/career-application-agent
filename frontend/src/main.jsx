import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

async function request(path, options) {
  const response = await fetch(`/api${path}`, options);
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Please check the fields and try again.');
  return body;
}

function App() {
  const [jobs, setJobs] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  async function refresh() { setJobs(await request('/jobs')); }
  useEffect(() => { refresh().catch(error => setMessage(error.message)); }, []);
  async function save(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form));
    if (!payload.source_url) payload.source_url = null;
    setBusy(true); setMessage('');
    try {
      await request('/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      form.reset();
      await refresh();
      setMessage('Job saved.');
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  }
  return <main>
    <p className="eyebrow">PROJECT 5 · PHASE 1</p>
    <h1>Career Application Agent</h1>
    <p>Save opportunities for evidence-based review. Application submission is disabled.</p>
    <section><h2>Add an opportunity</h2>
      <form onSubmit={save}>
        <label>Job title<input name="title" required maxLength={200} /></label>
        <label>Company<input name="company" required maxLength={200} /></label>
        <label>Source<select name="source_kind"><option value="pasted">Pasted job description</option><option value="daily_feed_manual">Daily jobs report — copied manually</option></select></label>
        <label>Original posting URL (optional)<input name="source_url" type="url" maxLength={2048} /></label>
        <label>Full job description<textarea name="description" required minLength={20} maxLength={50000} rows={8} /></label>
        <button disabled={busy}>{busy ? 'Saving…' : 'Save job'}</button>
      </form><p role="status" aria-live="polite">{message}</p>
    </section>
    <section><h2>Saved opportunities</h2><p>Showing up to 50 most recent jobs.</p>
      {jobs.length === 0 && <p>No jobs saved yet.</p>}
      {jobs.map(job => <article key={job.id}>
        <h3>{job.title}</h3><p>{job.company} · {job.source_kind === 'pasted' ? 'Pasted description' : 'Daily report'}</p>
        {job.source_url && <a href={job.source_url} target="_blank" rel="noreferrer">Open original posting</a>}
        <details><summary>Job description</summary><p className="description">{job.description}</p></details>
      </article>)}
    </section>
  </main>;
}
createRoot(document.getElementById('root')).render(<App />);
