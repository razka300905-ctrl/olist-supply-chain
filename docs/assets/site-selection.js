/* Project 1 - site selection page */
const D = window.DATA;
const REGION_SLOT = { SP: 0, SE: 1, AL: 1, BA: 1, PE: 1, MG: 2, RS: 3, GO: 4, DF: 4, RJ: 5 };   // colour follows the hub's region
const hubColor = st => SERIES[REGION_SLOT[st] ?? 0];
const asis = D.summary[0];
const scen = D.summary.filter(s => s.k >= 1);
const fcLabel = k => `${k} FC${k > 1 ? 's' : ''}`;

function card(row, label, col, f, df, lowerIsBetter) {
  const d = row[col] - asis[col];
  return { label, value: f(row[col]), note: `${df(d)} vs today`, tone: (d < 0) === lowerIsBetter ? 'good' : 'bad' };
}

function draw(k) {
  document.getElementById('k-val').textContent = fcLabel(k);
  const row = D.summary.find(s => s.k === k);
  kpis(document.getElementById('k-kpis'), [
    card(row, 'Avg distance', 'avg_km', v => `${Math.round(v)} km`, d => fmt.signed(d, 0, ' km'), true),
    card(row, 'Within 300 km', 'pct_within_300km', fmt.pct0, d => fmt.signed(d, 0, ' pp'), false),
    card(row, 'Within 800 km', 'pct_within_800km', fmt.pct0, d => fmt.signed(d, 0, ' pp'), false),
    card(row, 'Delivery time', 'est_delivery_days', v => `${fmt.n1(v)} days`, d => fmt.signed(d, 1, ' days'), true),
    card(row, 'Freight per item', 'est_freight_per_item', fmt.rs, d => fmt.signed(d, 2, ' R$'), true),
  ]);

  // Map
  const sites = D.sites.filter(s => s.k === k);
  const colorOf = Object.fromEntries(sites.map(s => [s.zone, hubColor(s.state)]));
  const a = D.assign.filter(z => z.k === k);
  plot('map', [
    { type: 'scattermap', mode: 'markers', lat: a.map(z => z.lat), lon: a.map(z => z.lng),
      marker: { size: a.map(z => Math.sqrt(Math.min(z.orders, 2000)) / 2.2 + 3), color: a.map(z => colorOf[z.fc_zone]), opacity: 0.7 },
      text: a.map(z => `Zone ${z.zone} (${z.state}) · ${fmt.int(z.orders)} orders · ${Math.round(z.road_km)} km to FC`),
      hovertemplate: '%{text}<extra></extra>' },
    { type: 'scattermap', mode: 'markers+text', lat: sites.map(s => s.lat), lon: sites.map(s => s.lng),
      marker: { size: 18, color: C.ink }, text: sites.map(s => title(s.city)), textposition: 'middle right',
      textfont: { size: 13, color: C.ink },
      customdata: sites.map(s => [s.state, fmt.int(s.orders_served), fmt.n1(s.share_pct), Math.round(s.avg_km_served)]),
      hovertemplate: '<b>FC %{text}-%{customdata[0]}</b><br>%{customdata[1]} orders (%{customdata[2]}%)<br>avg %{customdata[3]} km<extra></extra>' },
  ], { height: 540, margin: { l: 0, r: 0, t: 0, b: 0 }, map: { style: 'carto-positron', center: { lat: -15, lon: -52 }, zoom: 3 } });

  table(document.getElementById('sites-table'),
    [...sites].sort((x, y) => y.orders_served - x.orders_served).map(s => ({ ...s, site: `${title(s.city)}-${s.state}` })), [
      { key: 'site', label: 'Site' }, { key: 'orders_served', label: 'Orders', num: true, fmt: fmt.int },
      { key: 'share_pct', label: 'Share', fmt: fmt.pct0, bar: 100 }, { key: 'avg_km_served', label: 'Avg km', num: true, fmt: v => Math.round(v) },
    ]);
  document.getElementById('fc-value').innerHTML = k >= 2
    ? `<div class="callout note"><div class="ci">ℹ️</div><div><b>Value of FC #${k}:</b> about <b>R$ ${Math.round(row.marginal_freight_saving_per_year / 1000)}k/year</b>
       of freight. On freight alone it only pays off if it costs less than that to run.</div></div>` : '';

  // Trade-off curves (3 small multiples, one measure each)
  const panels = [['avg_km', 'Avg distance (km)'], ['pct_within_300km', 'Orders within 300 km (%)'], ['est_delivery_days', 'Est. delivery days']];
  const traces = [], lay = { height: 330, annotations: [], shapes: [], margin: { t: 48, b: 44, l: 40, r: 10 } };
  panels.forEach(([col, name], i) => {
    const ax = i ? i + 1 : '', w = 0.29, d0 = i * 0.355;
    traces.push({ type: 'scatter', mode: 'lines+markers', x: scen.map(s => s.k), y: scen.map(s => s[col]), xaxis: `x${ax}`, yaxis: `y${ax}`,
      line: { color: C.blue, width: 2.5 }, marker: { size: 9, color: C.blue, line: { color: '#fff', width: 2 } },
      hovertemplate: '%{x} FCs: %{y:.1f}<extra></extra>' });
    traces.push({ type: 'scatter', mode: 'markers', x: [k], y: [row[col]], xaxis: `x${ax}`, yaxis: `y${ax}`, hoverinfo: 'skip',
      marker: { size: 19, color: 'rgba(0,0,0,0)', line: { color: C.ink, width: 1.5 } } });
    lay[`xaxis${ax}`] = { domain: [d0, d0 + w], dtick: 1, title: { text: 'Number of FCs' }, gridcolor: '#efeee9', linecolor: '#c3c2b7' };
    lay[`yaxis${ax}`] = { anchor: `x${ax}`, gridcolor: '#efeee9', zeroline: false };
    lay.shapes.push({ type: 'line', xref: `x${ax}`, yref: `y${ax}`, x0: 0.7, x1: 6.3, y0: asis[col], y1: asis[col],
      line: { color: C.muted, dash: 'dash', width: 1.5 } });
    lay.annotations.push({ text: `<b>${name}</b>`, x: d0 + w / 2, y: 1.13, xref: 'paper', yref: 'paper', showarrow: false, font: { size: 13 } });
    lay.annotations.push({ text: 'today', x: 6.2, y: asis[col], xref: `x${ax}`, yref: `y${ax}`, showarrow: false, yshift: 9,
      font: { size: 10, color: C.muted } });
  });
  plot('curves', traces, lay);

  // Freight saved per added FC
  const m2 = scen.filter(s => s.k >= 2);
  plot('freight', [{ type: 'bar', x: m2.map(s => `${s.k} FCs`), y: m2.map(s => s.marginal_freight_saving_per_year / 1000),
    text: m2.map(s => `R$ ${Math.round(s.marginal_freight_saving_per_year / 1000)}k`), textposition: 'outside', cliponaxis: false,
    marker: { color: m2.map(s => s.k === k ? C.blue : C.light) }, hovertemplate: 'Adding FC #%{x}: R$ %{y:.0f}k/yr<extra></extra>' }],
    { height: 320, title: { text: 'Freight saved by adding each FC (R$ thousand / year)', font: { size: 13 } },
      yaxis: { range: [0, Math.max(...m2.map(s => s.marginal_freight_saving_per_year)) / 1000 * 1.25] } });
}

const slider = document.getElementById('k');
slider.oninput = () => draw(+slider.value);
draw(3);

table(document.getElementById('variants-table'), D.variants, [
  { key: 'variant', label: 'Network (3 FCs)' }, { key: 'avg_km', label: 'Avg km', num: true, fmt: v => Math.round(v) },
  { key: 'pct_within_300km', label: '≤300 km', num: true, fmt: fmt.pct0 },
  { key: 'extra_km_vs_optimal_pct', label: 'vs optimum', num: true, fmt: v => fmt.signed(v, 1, '%') },
]);
table(document.getElementById('all-table'), D.summary, [
  { key: 'scenario', label: 'Scenario' }, { key: 'avg_km', label: 'Avg km', num: true, fmt: v => Math.round(v) },
  { key: 'pct_within_300km', label: '≤300 km', num: true, fmt: fmt.pct1 }, { key: 'pct_within_800km', label: '≤800 km', num: true, fmt: fmt.pct1 },
  { key: 'est_delivery_days', label: 'Days', num: true, fmt: fmt.n2 }, { key: 'est_freight_per_item', label: 'Freight/item', num: true, fmt: fmt.rs },
  { key: 'est_freight_per_year', label: 'Freight/year', num: true, fmt: v => `R$ ${fmt.int(v)}` },
  { key: 'marginal_freight_saving_per_year', label: 'Saved by this FC', num: true, fmt: v => `R$ ${fmt.int(v)}` },
]);
