from __future__ import annotations
from pathlib import Path
import json
from typing import List, Dict

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Northwoods Events Viewer</title>
<style>
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 1rem; }
  header { display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
  .pill { display:inline-block; padding: .2rem .5rem; border:1px solid #ddd; border-radius:999px; margin-right:.5rem; font-size:.85rem;}
  #sources { min-width: 260px; }
  table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
  th, td { border-bottom: 1px solid #eee; padding: .5rem .4rem; vertical-align: top; }
  th { text-align: left; position: sticky; top: 0; background: #fff; }
  .muted { color:#666; }
  .ok { color: #0a7f2e; }
  .warn { color: #956400; }
  .err { color: #a40000; }
  .controls { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
  .tag { background:#f2f2f2; border-radius:4px; padding:.1rem .4rem; margin-right:.25rem; }
</style>
</head>
<body>
<header>
  <h1>Northwoods Events — Report</h1>
  <span id="stats" class="pill">loading…</span>
</header>

<section class="controls">
  <label for="sources">Filter by source:</label>
  <select id="sources" multiple size="6"></select>

  <label><input type="checkbox" id="onlyFuture" checked /> Only future</label>
  <label><input type="checkbox" id="groupBySource" /> Group by source</label>
  <input id="search" type="search" placeholder="Search title/location/url…" />
</section>

<section id="diags"></section>

<table id="tbl">
  <thead>
    <tr>
      <th>Start (UTC)</th>
      <th>Title</th>
      <th>Source</th>
      <th>Location</th>
      <th>Link</th>
    </tr>
  </thead>
  <tbody></tbody>
</table>

<script>
(async function(){
  const report = await fetch('report.json').then(r=>r.json());
  const srcLogs = report.source_logs || [];
  const preview = (report.events_preview || []);
  const allEvents = preview; // viewer shows preview; full ICS are downloadable

  const bySource = {};
  allEvents.forEach(ev => {
    (bySource[ev.source] ||= []).push(ev);
  });

  // Build source select
  const sel = document.getElementById('sources');
  Object.keys(bySource).sort().forEach(name=>{
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name + ' ('+(bySource[name].length||0)+')';
    sel.appendChild(opt);
  });

  // Stats + diagnostics
  const stats = document.getElementById('stats');
  stats.textContent = `${report.total_events} events • ${report.sources_processed} sources`;

  const diags = document.getElementById('diags');
  diags.innerHTML = `
    <h3>Source diagnostics</h3>
    <ul>
      ${srcLogs.map(s => `
        <li>
          <strong>${s.name}</strong> —
          <span class="${s.ok ? 'ok':'err'}">${s.ok ? 'OK':'ERROR'}</span>
          • events: ${s.count}
          ${s.error ? `• <span class="err">${s.error}</span>` : ''}
          ${s.diag && s.diag.api_url ? `• api: <code>${s.diag.api_url}</code>` : ''}
          ${s.diag && s.diag.fallback ? `• fallback: <code>${s.diag.fallback}</code>` : ''}
        </li>
      `).join('')}
    </ul>
    <p class="muted">Use the selector above to view one or more sources. Download ICS:
      <span class="tag"><a href="combined.ics">combined.ics</a></span>
      ${srcLogs.map(s=>`<span class="tag"><a href="by-source/${s.slug}.ics">${s.slug}.ics</a></span>`).join(' ')}
    </p>
  `;

  const tbody = document.querySelector('#tbl tbody');
  const onlyFuture = document.getElementById('onlyFuture');
  const groupBySource = document.getElementById('groupBySource');
  const search = document.getElementById('search');

  function getSelectedSources(){
    return [...sel.selectedOptions].map(o=>o.value);
  }

  function passFilters(ev) {
    const sel = getSelectedSources();
    if (sel.length && !sel.includes(ev.source)) return false;
    if (onlyFuture.checked) {
      const dt = new Date(ev.start_utc || ev.start || 0);
      if (isNaN(+dt) || dt < new Date()) return false;
    }
    const q = (search.value || '').toLowerCase();
    if (q) {
      const blob = [ev.title, ev.location, ev.url, ev.source].join(' ').toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  }

  function render() {
    tbody.innerHTML = '';
    let events = allEvents.filter(passFilters);
    if (groupBySource.checked) {
      const groups = {};
      events.forEach(e => (groups[e.source] ||= []).push(e));
      Object.keys(groups).sort().forEach(src => {
        const trh = document.createElement('tr');
        trh.innerHTML = `<td colspan="5"><strong>${src}</strong> <span class="muted">(${groups[src].length})</span></td>`;
        tbody.appendChild(trh);
        groups[src].sort((a,b)=> (a.start_utc||'').localeCompare(b.start_utc||'')).forEach(addRow);
      });
    } else {
      events.sort((a,b)=> (a.start_utc||'').localeCompare(b.start_utc||'')).forEach(addRow);
    }
  }

  function addRow(ev) {
    const tr = document.createElement('tr');
    const href = ev.url || '#';
    tr.innerHTML = `
      <td>${ev.start_utc || ''}</td>
      <td>${ev.title || ''}</td>
      <td>${ev.source || ''}</td>
      <td>${ev.location || ''}</td>
      <td><a href="${href}" target="_blank" rel="noopener">open</a></td>
    `;
    tbody.appendChild(tr);
  }

  sel.addEventListener('change', render);
  onlyFuture.addEventListener('change', render);
  groupBySource.addEventListener('change', render);
  search.addEventListener('input', render);

  render();
})();
</script>
</body>
</html>
"""

def write_index(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(TEMPLATE)
