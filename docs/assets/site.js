/* Shared helpers for every page: tabs, segmented controls, KPI cards, tables, Plotly defaults. */
const C = { blue: '#2a78d6', light: '#b7d3f6', orange: '#eb6834', aqua: '#1baf7a', amber: '#eda100',
            pink: '#e87ba4', green: '#008300', muted: '#898781', ink: '#0b0b0b' };
const SERIES = [C.blue, C.orange, C.aqua, C.amber, C.pink, C.green];

const fmt = {
  int: v => Math.round(v).toLocaleString('en-US'),
  n1: v => Number(v).toFixed(1),
  n2: v => Number(v).toFixed(2),
  pct0: v => `${Math.round(v)}%`,
  pct1: v => `${Number(v).toFixed(1)}%`,
  rs: v => `R$ ${Number(v).toFixed(2)}`,
  rsk: v => `R$ ${Math.round(v / 1000)}k`,
  signed: (v, d = 0, unit = '') => `${v > 0 ? '+' : ''}${Number(v).toFixed(d)}${unit}`,
};
const title = s => String(s).replace(/\b\w/g, c => c.toUpperCase());

/* Tabs: <div class="tabs"><button class="tab" data-tab="x"> ... <div class="panel" id="x"> */
function initTabs() {
  document.querySelectorAll('.tabs').forEach(bar => {
    bar.addEventListener('click', e => {
      const b = e.target.closest('.tab'); if (!b) return;
      bar.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t === b));
      document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === b.dataset.tab));
      window.dispatchEvent(new Event('resize'));      // let Plotly resize charts in a newly shown panel
    });
  });
}

/* Segmented control: seg(container, [{value, label}], initial, onChange) */
function seg(el, options, initial, onChange) {
  el.innerHTML = options.map(o => `<button data-v="${o.value}" class="${o.value === initial ? 'on' : ''}">${o.label}</button>`).join('');
  el.onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    el.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
    onChange(b.dataset.v);
  };
}

/* KPI cards: kpis(container, [{label, value, note, tone}]) */
function kpis(el, items) {
  el.className = `grid c${Math.min(items.length, 5)}`;
  el.innerHTML = items.map(k => `<div class="card"><div class="label">${k.label}</div><div class="value">${k.value}</div>
    <div class="note ${k.tone || ''}">${k.note || ''}</div></div>`).join('');
}

/* Table: table(container, rows, [{key, label, num, fmt, bar}]) - bar: max value for an inline bar */
function table(el, rows, cols) {
  const head = cols.map(c => `<th class="${c.num ? 'num' : ''}">${c.label}</th>`).join('');
  const body = rows.map(r => '<tr>' + cols.map(c => {
    const v = r[c.key];
    const txt = v === null || v === undefined || Number.isNaN(v) ? '–' : (c.fmt ? c.fmt(v, r) : v);
    if (c.bar) {
      const w = Math.max(2, Math.min(100, (v / c.bar) * 100));
      return `<td><div class="bar-cell"><div class="b" style="width:${w * 0.6}px"></div>${txt}</div></td>`;
    }
    return `<td class="${c.num ? 'num' : ''}">${txt}</td>`;
  }).join('') + '</tr>').join('');
  el.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

/* Plotly defaults: one look for every chart */
const PLOT_CONFIG = { displayModeBar: false, responsive: true };
function layout(extra = {}) {
  const base = {
    font: { family: 'Inter, system-ui, sans-serif', size: 12, color: '#3d3c39' },
    paper_bgcolor: '#fff', plot_bgcolor: '#fff', margin: { l: 48, r: 16, t: 44, b: 44 },
    hoverlabel: { bgcolor: '#fff', bordercolor: '#e1e0d9', font: { family: 'Inter', color: '#0b0b0b' } },
    xaxis: { gridcolor: '#efeee9', linecolor: '#c3c2b7', zeroline: false, automargin: true },
    yaxis: { gridcolor: '#efeee9', linecolor: '#c3c2b7', zeroline: false, automargin: true },
    showlegend: false, bargap: 0.32,
  };
  return deepMerge(base, extra);
}
function deepMerge(a, b) {
  const out = { ...a };
  for (const [k, v] of Object.entries(b)) {
    out[k] = v && typeof v === 'object' && !Array.isArray(v) && typeof a[k] === 'object' ? deepMerge(a[k], v) : v;
  }
  return out;
}
const plot = (id, traces, lay) => Plotly.react(id, traces, layout(lay), PLOT_CONFIG);

/* Small multiples of bars sharing one x: panels = [{title, y, text}] , highlight index or array of booleans */
function barPanels(id, x, panels, highlight, height = 320) {
  const n = panels.length, gap = 0.06, w = (1 - gap * (n - 1)) / n;
  const traces = [], lay = { height, annotations: [], margin: { t: 48, b: 40, l: 36, r: 10 } };
  panels.forEach((p, i) => {
    const ax = i === 0 ? '' : i + 1;
    traces.push({ type: 'bar', x, y: p.y, xaxis: `x${ax}`, yaxis: `y${ax}`, text: p.text, textposition: 'outside',
      cliponaxis: false, hovertemplate: '%{x}: %{text}<extra></extra>',
      marker: { color: x.map((_, j) => (Array.isArray(highlight) ? highlight[j] : j === highlight) ? C.blue : C.light) } });
    const d0 = i * (w + gap);
    lay[`xaxis${ax}`] = { domain: [d0, d0 + w], gridcolor: '#efeee9', linecolor: '#c3c2b7', tickfont: { size: 10.5 }, automargin: true };
    lay[`yaxis${ax}`] = { anchor: `x${ax}`, range: [0, Math.max(...p.y) * 1.3], gridcolor: '#efeee9', zeroline: false };
    lay.annotations.push({ text: `<b>${p.title}</b>`, x: d0 + w / 2, y: 1.12, xref: 'paper', yref: 'paper',
      showarrow: false, font: { size: 13, color: C.ink } });
  });
  plot(id, traces, lay);
}

document.addEventListener('DOMContentLoaded', initTabs);
