/* Project 2 - vehicle routing page */
const D = window.DATA;
const TYPE_COLOR = { van: C.blue, motorbike: C.orange };
const FLEETS = { van_only: 'Van only', motorbike_only: 'Motorbike only', mixed: 'Mixed fleet' };
const DAYS = { normal: 'Normal day', black_friday: 'Black Friday' };
const sc = Object.fromEntries(D.scenarios.map(s => [s.scenario, s]));
let day = 'normal', fleet = 'mixed';

function drawFleetControl() {
  const opts = Object.entries(FLEETS).map(([value, label]) => ({ value, label }));
  if (day === 'black_friday') opts.push({ value: 'normal_fleet', label: 'Normal-day fleet only' });
  if (day === 'normal' && fleet === 'normal_fleet') fleet = 'mixed';
  seg(document.getElementById('fleet'), opts, fleet, v => { fleet = v; draw(); });
}

function draw() {
  const sid = `${day}__${fleet}`, r = sc[sid];
  const rt = D.routes.filter(x => x.scenario === sid);
  const costCard = fleet === 'normal_fleet'
    ? { label: 'Cost per delivered order', value: fmt.rs(r.cost_per_order), note: 'fleet capped' }
    : { label: 'Cost per order', value: fmt.rs(r.cost_per_order), note: `↓ ${Math.round(r.cost_saving_vs_baseline_pct)}% vs greedy plan`, tone: 'good' };
  const why = r.orders_too_big_for_fleet ? 'too bulky for a motorbike' : (r.orders_not_delivered ? 'fleet too small' : 'all delivered');
  kpis(document.getElementById('s-kpis'), [
    { label: 'Vehicles used', value: r.vans + r.motorbikes, note: `${r.vans} van · ${r.motorbikes} moto` },
    { label: 'Total distance', value: `${fmt.int(r.total_km)} km`, note: `${fmt.n1(r.km_per_order)} km per order` },
    costCard,
    { label: 'Longest route', value: `${fmt.n1(r.max_route_hours)} h`, note: 'shift limit = 9 h' },
    { label: 'Not delivered', value: r.orders_not_delivered, note: why, tone: r.orders_not_delivered ? 'bad' : 'good' },
  ]);

  // Route map: one trace per route, coloured by vehicle type
  const traces = [], shown = new Set();
  const byRoute = {};
  rt.forEach(x => (byRoute[x.route] ||= []).push(x));
  Object.entries(byRoute).forEach(([id, stops]) => {
    stops.sort((a, b) => a.seq - b.seq);
    const t = stops[0].vehicle_type;
    traces.push({ type: 'scattermap', mode: 'lines+markers', lat: stops.map(s => s.lat), lon: stops.map(s => s.lng),
      line: { width: 2.5, color: TYPE_COLOR[t] }, marker: { size: 7, color: TYPE_COLOR[t] },
      name: title(t), legendgroup: t, showlegend: !shown.has(t),
      text: stops.map(s => `Route ${id} (${t}) · stop ${s.seq} · ${title(s.city)} · ${String(Math.floor(s.arrival_min / 60)).padStart(2, '0')}:${String(Math.round(s.arrival_min % 60)).padStart(2, '0')} into shift`),
      hovertemplate: '%{text}<extra></extra>' });
    shown.add(t);
  });
  traces.push({ type: 'scattermap', mode: 'markers', lat: [D.depot.lat], lon: [D.depot.lng], marker: { size: 18, color: C.ink },
    showlegend: false, hovertemplate: 'FC São Paulo<extra></extra>' });
  traces.push({ type: 'scattermap', mode: 'text', lat: [D.depot.lat], lon: [D.depot.lng], text: ['FC São Paulo'],
    textposition: 'bottom right', textfont: { size: 13, color: C.ink }, showlegend: false, hoverinfo: 'skip' });
  const mean = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
  plot('map', traces, { height: 520, margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: true,
    legend: { orientation: 'h', x: 0.01, y: 0.99, bgcolor: 'rgba(255,255,255,.85)' },
    map: { style: 'carto-positron', center: { lat: mean(rt.map(x => x.lat)), lon: mean(rt.map(x => x.lng)) }, zoom: 8.6 } });

  // Route table
  const per = Object.entries(byRoute).map(([id, s]) => ({ route: +id, vehicle: s[0].vehicle_type,
    stops: s.filter(x => x.order_id === 1).length, km: s[0].route_km, hours: s[0].route_min / 60, load: s[0].volume_util_pct }));
  table(document.getElementById('routes-table'), per, [
    { key: 'route', label: 'Route', num: true }, { key: 'vehicle', label: 'Vehicle', fmt: title },
    { key: 'stops', label: 'Stops', num: true }, { key: 'km', label: 'Km', num: true, fmt: v => Math.round(v) },
    { key: 'hours', label: 'Hours (of 9)', fmt: fmt.n1, bar: 9 }, { key: 'load', label: 'Load (vol.)', num: true, fmt: fmt.pct0 },
  ]);

  const cities = D.cities.filter(c => c.day === day).map(c => ({ ...c, city: title(c.city) }));
  table(document.getElementById('cities-table'), cities, [
    { key: 'city', label: 'Municipality' }, { key: 'orders', label: 'Orders', num: true },
    { key: 'share_pct', label: 'Share', fmt: fmt.pct0, bar: 100 },
  ]);
}

seg(document.getElementById('day'), Object.entries(DAYS).map(([value, label]) => ({ value, label })), day,
    v => { day = v; drawFleetControl(); draw(); });
drawFleetControl();
draw();

// Cost comparison: one panel per day
const fleetKeys = Object.keys(FLEETS);
const traces = [], lay = { height: 340, annotations: [], margin: { t: 50, b: 40, l: 50, r: 10 } };
const maxCost = Math.max(...D.scenarios.filter(s => FLEETS[s.fleet]).map(s => s.cost_per_order));
['normal', 'black_friday'].forEach((d, i) => {
  const rows = fleetKeys.map(f => sc[`${d}__${f}`]);
  const best = rows.reduce((a, b) => (b.cost_per_order < a.cost_per_order ? b : a));
  const ax = i ? 2 : '', d0 = i * 0.53;
  traces.push({ type: 'bar', x: fleetKeys.map(f => FLEETS[f]), y: rows.map(r => r.cost_per_order), xaxis: `x${ax}`, yaxis: `y${ax}`,
    text: rows.map(r => fmt.rs(r.cost_per_order)), textposition: 'outside', cliponaxis: false,
    marker: { color: rows.map(r => r === best ? C.blue : C.light) },
    customdata: rows.map(r => [r.vans, r.motorbikes, r.orders_not_delivered]),
    hovertemplate: '%{x}: %{text} per order<br>%{customdata[0]} vans, %{customdata[1]} motorbikes<br>%{customdata[2]} not delivered<extra></extra>' });
  lay[`xaxis${ax}`] = { domain: [d0, d0 + 0.47], linecolor: '#c3c2b7' };
  lay[`yaxis${ax}`] = { anchor: `x${ax}`, range: [0, maxCost * 1.25], gridcolor: '#efeee9', title: i ? undefined : { text: 'R$ per delivered order' } };
  lay.annotations.push({ text: `<b>${DAYS[d]} (${rows[0].orders} orders)</b>`, x: d0 + 0.235, y: 1.12, xref: 'paper', yref: 'paper',
    showarrow: false, font: { size: 13 } });
});
plot('cost', traces, lay);

table(document.getElementById('all-table'), D.scenarios, [
  { key: 'scenario', label: 'Scenario' }, { key: 'vans', label: 'Vans', num: true }, { key: 'motorbikes', label: 'Motos', num: true },
  { key: 'total_km', label: 'Km', num: true, fmt: v => fmt.int(v) }, { key: 'total_cost', label: 'Cost', num: true, fmt: v => `R$ ${fmt.int(v)}` },
  { key: 'cost_per_order', label: 'R$/order', num: true, fmt: fmt.n2 }, { key: 'orders_not_delivered', label: 'Not delivered', num: true },
  { key: 'cost_saving_vs_baseline_pct', label: 'vs greedy', num: true, fmt: v => fmt.signed(-v, 0, '%') },
]);
