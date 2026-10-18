/* Project 0 - data cleaning page */
const D = window.DATA;

// Rows kept vs removed (log scale)
const rows = D.rows.filter(r => r.table !== 'geo_zip_centroid');
plot('rows-chart', [
  { type: 'bar', orientation: 'h', name: 'Kept', y: rows.map(r => r.table), x: rows.map(r => r.clean_rows),
    marker: { color: C.blue }, hovertemplate: '%{y}: %{x:,} rows kept<extra></extra>' },
  { type: 'bar', orientation: 'h', name: 'Removed', y: rows.map(r => r.table),
    x: rows.map(r => Math.max(0, (r.raw_rows || 0) - r.clean_rows)), marker: { color: C.muted },
    hovertemplate: '%{y}: %{x:,} rows removed<extra></extra>' },
], { barmode: 'stack', height: 360, showlegend: true, legend: { orientation: 'h', y: 1.12, x: 0 },
     xaxis: { type: 'log', title: { text: 'Rows (log scale)' } }, margin: { l: 150, t: 40 } });

// Cleaning log with a table filter
const sel = document.getElementById('log-filter');
const tables = ['All', ...new Set(D.rules.map(r => r.table))];
sel.innerHTML = tables.map(t => `<option>${t}</option>`).join('');
const logCols = [
  { key: 'table', label: 'Table' }, { key: 'rule', label: 'Issue / rule' },
  { key: 'rows_affected', label: 'Rows', num: true, fmt: fmt.int }, { key: 'action', label: 'Action' },
];
const drawLog = () => table(document.getElementById('log-table'),
  sel.value === 'All' ? D.rules : D.rules.filter(r => r.table === sel.value), logCols);
sel.onchange = drawLog;
drawLog();

table(document.getElementById('check-table'), D.checks, [
  { key: 'rule', label: 'Check' }, { key: 'action', label: 'Result', fmt: v => `✅ ${v.trim()}` },
]);
