/* Project 3 - inventory page */
const D = window.DATA;
const T = D.tradeoff;
const chosen = T.find(r => r.sweep === 'stock_rule' && r.stock_rule_min_weeks === 6);
const isChosen = r => r.stock_rule_min_weeks === 6 && r.service_level_pct === 95 && r.order_cap_weeks === '8' && r.forecast_method === 'ses';

// ---------- 1. trade-off explorer
const SWEEPS = {
  stock_rule: { label: 'How many products?', key: 'stock_rule_min_weeks', name: v => `≥${v}/12 wk`,
    note: 'Going deeper into the range doubles the FC share but almost doubles the cost of every unit. ≥6 of 12 weeks is the balance.' },
  service_level: { label: 'Which service level?', key: 'service_level_pct', name: v => `${v}%`,
    note: 'From 50% to 95% the fill rate rises ~3 points. Above 95% stock grows but fill rate does not: the misses come mostly from newly listed products still waiting for their first delivery.' },
  order_cap: { label: 'How much to order at once?', key: 'order_cap_weeks', name: v => (v === 'EOQ only' ? 'pure EOQ' : `cap ${v} wk`),
    note: 'Pure EOQ is ~2% cheaper on paper but holds 15 weeks of stock. A 4-week cap means many small orders; 8 weeks is the middle ground.' },
};
function drawSweep(sweep) {
  const s = SWEEPS[sweep];
  const rows = T.filter(r => r.sweep === sweep).sort((a, b) => (parseFloat(a[s.key]) || 999) - (parseFloat(b[s.key]) || 999));
  const x = rows.map(r => s.name(r[s.key]));
  barPanels('sweep-chart', x, [
    { title: 'Units from FC (%)', y: rows.map(r => r.fc_share_of_all_units_pct), text: rows.map(r => fmt.pct1(r.fc_share_of_all_units_pct)) },
    { title: 'Fill rate (%)', y: rows.map(r => r.fill_rate_pct), text: rows.map(r => fmt.pct1(r.fill_rate_pct)) },
    { title: 'Cost per unit (R$)', y: rows.map(r => r.cost_per_unit_served), text: rows.map(r => fmt.rs(r.cost_per_unit_served)) },
    { title: 'Weeks of cover', y: rows.map(r => r.weeks_of_cover), text: rows.map(r => fmt.n1(r.weeks_of_cover)) },
  ], rows.map(isChosen), 340);
  document.getElementById('sweep-note').innerHTML = `<div class="callout insight"><div class="ci">💡</div><div>${s.note}</div></div>`;
}
seg(document.getElementById('sweep'), Object.entries(SWEEPS).map(([value, v]) => ({ value, label: v.label })), 'stock_rule', drawSweep);
drawSweep('stock_rule');
const st = T.find(r => r.sweep === 'planning');
document.getElementById('static-note').innerHTML = `<div class="callout note"><div class="ci">ℹ️</div><div><b>Fixed list vs. weekly re-planning:</b>
  a list set once is cheaper per unit (${fmt.rs(st.cost_per_unit_served)}), but the FC ships only <b>${fmt.pct1(st.fc_share_of_all_units_pct)}</b>
  of units (vs ${fmt.pct1(chosen.fc_share_of_all_units_pct)}) and holds <b>${fmt.n1(st.weeks_of_cover)} weeks</b> of ageing stock
  (vs ${fmt.n1(chosen.weeks_of_cover)}).</div></div>`;

// ---------- 2. long tail + ABC matrix
plot('curve', [{ type: 'scatter', mode: 'lines', x: D.curve.map(c => c.skus), y: D.curve.map(c => c.units_covered_pct),
  fill: 'tozeroy', fillcolor: 'rgba(42,120,214,0.10)', line: { color: C.blue, width: 2.5 },
  hovertemplate: 'Top %{x:,} products → %{y:.1f}% of units<extra></extra>' }],
  { height: 330, title: { text: 'Products needed to cover x% of units', font: { size: 13 } },
    xaxis: { type: 'log', title: { text: 'Number of products (log scale)' } }, yaxis: { range: [0, 100], title: { text: '% of units' } } });
const top100 = D.curve.find(c => c.skus === 100);
document.getElementById('tail-note').innerHTML = `Of <b>${fmt.int(D.seg.products_total)} products</b> sold in the calibration weeks,
  the top 100 cover only <b>${Math.round(top100.units_covered_pct)}%</b> of units.`;
table(document.getElementById('matrix-table'), D.matrix.index.map((abc, i) =>
  Object.fromEntries([['abc', abc], ...D.matrix.columns.map((c, j) => [c, D.matrix.values[i][j]])])),
  [{ key: 'abc', label: 'ABC' }, ...D.matrix.columns.map(c => ({ key: c, label: c, num: true, fmt: fmt.int }))]);

// ---------- 3. reorder plan
const cat = document.getElementById('cat');
cat.innerHTML = ['All', ...[...new Set(D.plan.map(p => p.category))].sort()].map(c => `<option>${c}</option>`).join('');
const drawPlan = () => table(document.getElementById('plan-table'), cat.value === 'All' ? D.plan : D.plan.filter(p => p.category === cat.value), [
  { key: 'category', label: 'Category' }, { key: 'price', label: 'Price', num: true, fmt: v => `R$ ${Math.round(v)}` },
  { key: 'forecast_week', label: 'Forecast/wk', num: true, fmt: fmt.n1 }, { key: 'lead_days', label: 'Lead time (d)', num: true },
  { key: 'safety_stock', label: 'Safety stock', num: true, fmt: fmt.n1 }, { key: 'reorder_point', label: 'Reorder at', num: true },
  { key: 'order_qty', label: 'Order qty', num: true }, { key: 'fill_rate_pct', label: 'Fill rate (test)', fmt: fmt.pct0, bar: 100 },
]);
cat.onchange = drawPlan;
drawPlan();

// ---------- 4. forecast methods, two levels
const ORDER = ['naive', 'ma4', 'ses', 'holt', 'holt_damped', 'croston', 'tsb'];
const NAMES = { naive: 'Naive', ma4: 'MA 4 wk', ses: 'SES', holt: 'Holt', holt_damped: 'Holt damped', croston: 'Croston', tsb: 'TSB' };
function drawProductLevel() {
  const f = Object.fromEntries(D.fc.map(r => [r.method, r]));
  const stock = Object.fromEntries(T.filter(r => r.sweep === 'forecast').map(r => [r.forecast_method, r]));
  barPanels('fc-chart', ORDER.map(m => NAMES[m]), [
    { title: 'Error: WAPE (%)', y: ORDER.map(m => f[m].wape_pct), text: ORDER.map(m => fmt.pct0(f[m].wape_pct)) },
    { title: 'Error: scaled RMSE (%)', y: ORDER.map(m => f[m].scaled_rmse_pct), text: ORDER.map(m => fmt.pct0(f[m].scaled_rmse_pct)) },
    { title: 'Stock needed (R$k)', y: ORDER.map(m => stock[m].avg_inventory_value / 1000), text: ORDER.map(m => `${Math.round(stock[m].avg_inventory_value / 1000)}k`) },
  ], ORDER.indexOf('ses'), 340);
  document.getElementById('fc-note').innerHTML = `<div class="callout insight"><div class="ci">💡</div><div><b>The two error metrics disagree</b>
    (WAPE favours forecasts near zero, which flatters naive), so the method is chosen on the <b>stock outcome</b>.
    <b>SES</b> keeps the fill rate of the moving average (${fmt.pct1(stock.ses.fill_rate_pct)} vs ${fmt.pct1(stock.ma4.fill_rate_pct)})
    with ~9% less stock. Holt adds nothing (no trend); Croston/TSB hold little stock but miss more orders.
    <b>Holt-Winters is not usable here:</b> it needs two years of history, and weeks full of zeros have no seasonal shape.</div></div>`;
}
function drawDailyLevel() {
  const rows = [...D.daily].sort((a, b) => b.wape_pct - a.wape_pct);
  const best = D.daily.reduce((a, b) => (b.wape_pct < a.wape_pct ? b : a));
  plot('daily-bars', [{ type: 'bar', orientation: 'h', y: rows.map(r => r.label), x: rows.map(r => r.wape_pct),
    text: rows.map(r => fmt.pct1(r.wape_pct)), textposition: 'outside', cliponaxis: false,
    marker: { color: rows.map(r => r === best ? C.blue : C.light) }, hovertemplate: '%{y}: %{x:.1f}% WAPE<extra></extra>' }],
    { height: 380, title: { text: '7-day-ahead error (WAPE %)', font: { size: 13 } }, margin: { l: 190 },
      xaxis: { range: [0, Math.max(...rows.map(r => r.wape_pct)) * 1.2] } });
  const s = D.dailySeries;
  plot('daily-line', [
    { type: 'scatter', mode: 'lines', name: 'Actual', x: s.map(r => r.date), y: s.map(r => r.actual), line: { color: C.muted, width: 1.5 } },
    { type: 'scatter', mode: 'lines', name: best.label, x: s.map(r => r.date), y: s.map(r => r[best.method]), line: { color: C.blue, width: 2.5 } },
  ], { height: 380, showlegend: true, legend: { orientation: 'h', y: 1.12, x: 0 },
       title: { text: 'Actual vs. forecast, test period (units per day)', font: { size: 13 } }, margin: { t: 64 } });
  const ma7 = D.daily.find(r => r.method === 'ma7');
  document.getElementById('daily-note').innerHTML = `<div class="callout insight"><div class="ci">💡</div><div>The FC's daily volume has
    a clear weekday pattern (Mon ${fmt.n2(D.weekday.Mon)}× average, Sat ${fmt.n2(D.weekday.Sat)}×). <b>${best.label}</b> wins with
    <b>${fmt.pct1(best.wape_pct)}</b> error and almost no bias, ~28% better than a 7-day moving average (${fmt.pct1(ma7.wape_pct)}).
    The weekday season does the work; the trend term adds almost nothing. Use it to plan pickers and next-day vehicles.</div></div>`;
}
let dailyDrawn = false;
seg(document.getElementById('level'), [{ value: 'product', label: 'Per product, per week' }, { value: 'daily', label: 'FC total, per day' }],
  'product', v => {
    document.getElementById('fc-product').style.display = v === 'product' ? '' : 'none';
    document.getElementById('fc-daily').style.display = v === 'daily' ? '' : 'none';
    if (v === 'daily' && !dailyDrawn) { drawDailyLevel(); dailyDrawn = true; }
    window.dispatchEvent(new Event('resize'));
  });
drawProductLevel();

table(document.getElementById('all-table'), T, [
  { key: 'sweep', label: 'Sweep' }, { key: 'stock_rule_min_weeks', label: 'Rule', num: true },
  { key: 'service_level_pct', label: 'CSL', num: true, fmt: fmt.pct0 }, { key: 'order_cap_weeks', label: 'Cap' },
  { key: 'forecast_method', label: 'Forecast' }, { key: 'planning', label: 'Planning' },
  { key: 'fill_rate_pct', label: 'Fill', num: true, fmt: fmt.pct1 }, { key: 'fc_share_of_all_units_pct', label: 'FC share', num: true, fmt: fmt.pct1 },
  { key: 'avg_inventory_value', label: 'Stock', num: true, fmt: fmt.rsk }, { key: 'weeks_of_cover', label: 'Cover (wk)', num: true, fmt: fmt.n1 },
  { key: 'cost_per_unit_served', label: 'R$/unit', num: true, fmt: fmt.n2 },
]);
