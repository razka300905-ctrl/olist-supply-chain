"""Build the static portfolio site (GitHub Pages) from the project outputs.

    .venv/Scripts/python docs/build.py

Reads the CSV results of every project and the ANALYSIS.md files, and writes docs/*.html. Each page embeds
the data it needs as JSON (window.DATA), so the site works as plain files: no server, no Python at runtime.
Static text and headline KPIs are rendered here (fast first paint, readable without JavaScript); charts,
maps and scenario pickers are drawn in the browser by docs/assets/*.js with Plotly.js.
"""
from html import escape
import json
from pathlib import Path

import markdown
import pandas as pd

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
SITE, VRP, INV, PIPE = (ROOT / "site_selection" / "outputs", ROOT / "vrp" / "outputs",
                        ROOT / "inventory" / "outputs", ROOT / "data_pipeline" / "reports")

AUTHOR = "Razka"
GITHUB = "https://github.com/razka300905-ctrl/olist-supply-chain"
LINKEDIN = ""                                   # add your LinkedIn URL here
STREAMLIT = "https://site-selection-vrp.streamlit.app/"
PLOTLY = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/3.0.1/plotly.min.js"

PAGES = [("index.html", "Home"), ("data.html", "0 · Data"), ("site-selection.html", "1 · Where"),
         ("vrp.html", "2 · How"), ("inventory.html", "3 · What")]


# ------------------------------------------------------------------ HTML components
def hero(eyebrow, title, subtitle, chips=(), cta=""):
    chip_html = "".join(f'<span class="chip">{escape(c)}</span>' for c in chips)
    return (f'<header class="hero"><div class="eyebrow">{escape(eyebrow)}</div><h1>{escape(title)}</h1>'
            f'<p>{subtitle}</p>{f"<div class=chips>{chip_html}</div>" if chips else ""}{cta}</header>')


def purpose(question, objective, output, users):
    items = [("❓", "Business question", question), ("🎯", "Objective", objective),
             ("📦", "Output", output), ("👥", "Who uses it", users)]
    return '<div class="grid c4">' + "".join(
        f'<div class="card accent"><div class="icon">{i}</div><h3>{t}</h3><p>{b}</p></div>' for i, t, b in items) + "</div>"


def kpis(items):
    return f'<div class="grid c{min(len(items), 5)}">' + "".join(
        f'<div class="card"><div class="label">{escape(k[0])}</div><div class="value">{escape(str(k[1]))}</div>'
        f'<div class="note {k[3] if len(k) > 3 else ""}">{k[2]}</div></div>' for k in items) + "</div>"


def cards(items, cols=3):
    return f'<div class="grid c{cols}">' + "".join(
        f'<div class="card"><div class="icon">{i}</div><h3>{t}</h3><p>{b}</p></div>' for i, t, b in items) + "</div>"


def callout(text, kind="recommend"):
    icon = {"recommend": "✅", "insight": "💡", "note": "ℹ️"}[kind]
    return f'<div class="callout {kind}"><div class="ci">{icon}</div><div>{text}</div></div>'


def section(num, title, sub=""):
    return (f'<div class="section"><div class="num">{num}</div><h2>{escape(title)}</h2></div>'
            + (f'<p class="ssub">{sub}</p>' if sub else ""))


def tabs(items):
    """items: [(id, label)] -> tab bar; the first tab is active."""
    return '<div class="tabs">' + "".join(
        f'<button class="tab{" active" if i == 0 else ""}" data-tab="{k}">{lbl}</button>' for i, (k, lbl) in enumerate(items)) + "</div>"


def panel(pid, html, active=False):
    return f'<section class="panel{" active" if active else ""}" id="{pid}">{html}</section>'


def analysis(md_path):
    html = markdown.markdown(md_path.read_text(encoding="utf-8"), extensions=["tables"])
    return f'<div class="prose">{html}</div>'


def page(filename, title, description, body, data=None, script=None):
    nav = "".join(f'<a href="{f}" class="{"active" if f == filename else ""}">{lbl}</a>' for f, lbl in PAGES)
    nav += f'<a class="ext" href="{STREAMLIT}" target="_blank" rel="noopener">Interactive lab ↗</a>'
    nav += f'<a class="ext" href="{GITHUB}" target="_blank" rel="noopener">GitHub ↗</a>'
    scripts = ""
    if data is not None:
        payload = json.dumps(data, separators=(",", ":"), default=float).replace("</", "<\\/")
        scripts = (f'<script src="{PLOTLY}"></script><script src="assets/site.js"></script>'
                   f'<script>window.DATA={payload};</script><script src="assets/{script}"></script>')
    links = " · ".join(f'<a href="{u}" target="_blank" rel="noopener">{n}</a>'
                       for n, u in [("GitHub", GITHUB), ("LinkedIn", LINKEDIN), ("Interactive lab", STREAMLIT)] if u)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · Olist Supply Chain Portfolio</title>
<meta name="description" content="{escape(description)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📦</text></svg>">
</head>
<body>
<nav class="nav"><div class="wrap"><a class="brand" href="index.html">Olist <span>Supply Chain</span></a><div class="nav-links">{nav}</div></div></nav>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">Built by {AUTHOR} · {links}<br>
Data: Olist Brazilian E-Commerce Public Dataset (Kaggle, CC BY-NC-SA 4.0). Costs, speeds and capacities not in the data are marked assumptions.</div></footer>
{scripts}
</body>
</html>
"""
    (DOCS / filename).write_text(html, encoding="utf-8")
    print(f"  {filename:<22}{len(html) / 1024:7.0f} KB")


def records(df, cols=None, digits=3):
    d = df[cols] if cols else df
    return json.loads(d.round(digits).to_json(orient="records"))


# ------------------------------------------------------------------ pages
def build_home():
    s = pd.read_csv(SITE / "scenario_summary.csv")
    asis, k3 = s.iloc[0], s[s.k == 3].iloc[0]
    vrp = pd.read_csv(VRP / "vrp_scenarios.csv").set_index("scenario")
    inv = pd.read_csv(INV / "policy_tradeoff.csv")
    chosen = inv[(inv.sweep == "stock_rule") & (inv.stock_rule_min_weeks == 6)].iloc[0]
    nm = vrp.loc["normal__mixed"]

    cta = (f'<div class="cta"><a class="btn white" href="#answers">See the answers ↓</a>'
           f'<a class="btn ghost" href="{STREAMLIT}" target="_blank" rel="noopener">Open the interactive lab ↗</a>'
           f'<a class="btn ghost" href="{GITHUB}" target="_blank" rel="noopener">Code on GitHub ↗</a></div>')
    body = hero(f"Supply chain portfolio · Olist, Brazil · by {AUTHOR}", "From marketplace to fulfilment network",
                "An end-to-end study on ~100k real e-commerce orders. It asks how Olist could deliver faster by running its "
                "own fulfilment centres: <b>where</b> to put them, <b>how</b> to deliver from them, and <b>what</b> to stock in them.",
                ["Python", "SQL", "Optimisation (MILP · OR-Tools)", "Forecasting", "Simulation"], cta)

    body += section(1, "Why this research?", "The problem, the objective and what the research delivers")
    body += cards([
        ("🚚", "The problem", "Olist is a marketplace: <b>every seller ships directly</b> to the customer. 76% of items leave "
                             "São Paulo state, but only 42% of orders go there, so the average parcel travels <b>~775 km</b> "
                             "and takes <b>12 days</b>."),
        ("🎯", "The objective", "Design a <b>fulfilment-centre (FC) model</b> end to end, and quantify its trade-offs in "
                               "service, cost and capital, to support a real go / no-go decision."),
        ("❓", "The main question", "<b>Should Olist run its own FC network, and if so, how?</b> It splits into three linked "
                                   "decisions: where (network), how (delivery) and what (stock)."),
        ("📦", "Outputs", "A recommended FC network · daily routes and fleet mix · a stock list with reorder points · "
                         "forecast comparison · trade-off curves · reproducible Python + SQL."),
        ("👥", "Who it is for", "Supply-chain and operations leaders deciding on network, fleet and inventory, and product "
                               "managers building fulfilment services for sellers."),
        ("🧭", "How to read it", "Every project page follows the same order: <b>purpose → answer → results → analysis → "
                                "method</b>. Start with the answers below."),
    ])

    body += '<div id="answers"></div>' + section(2, "Three questions, three answers", "Each project answers one decision and feeds the next")
    body += '<div class="grid c3">' + "".join(
        f'<a class="card accent" href="{href}"><div class="icon">{icon}</div><h3>{t}</h3><p class="q">{q}</p><p>{a}</p>'
        f'<span class="more">Open the project →</span></a>' for icon, t, q, a, href in [
            ("📍", "1 · Where?", "How many FCs, and where?",
             f"<b>3 FCs</b>: São Paulo, Minas Gerais/Rio, Northeast. Distance <b>−47%</b>, next-day reach "
             f"<b>{asis.pct_within_300km:.0f}% → {k3.pct_within_300km:.0f}%</b>.", "site-selection.html"),
            ("🚚", "2 · How?", "How should the São Paulo FC deliver every day?",
             f"<b>Mixed fleet</b> (vans + motorbikes): <b>R$ {nm.cost_per_order:.2f}</b> per order on a normal day. "
             "Black Friday needs <b>~4×</b> the vehicles.", "vrp.html"),
            ("📦", "3 · What?", "What should the FC stock, and how much?",
             f"<b>~{int(chosen.products_listed_last_week)} regular products</b>, re-planned weekly: "
             f"{chosen.fc_share_of_all_units_pct:.0f}% of units from FC stock, <b>R$ {chosen.avg_inventory_value / 1000:.0f}k</b> of inventory.",
             "inventory.html")]) + "</div>"

    body += section(3, "Headline numbers")
    body += kpis([
        ("Orders analysed", "99,441", "2016–2018, all of Brazil"),
        ("Data cleaned", "1.55M rows", "9 tables · 17 checks pass"),
        ("Avg distance (3 FCs)", f"{k3.avg_km:.0f} km", f"−47% vs {asis.avg_km:.0f} km today", "good"),
        ("Next-day reach", f"{k3.pct_within_300km:.0f}%", f"+{k3.pct_within_300km - asis.pct_within_300km:.0f} pp vs today", "good"),
        ("Cost per delivery", f"R$ {nm.cost_per_order:.0f}", f"optimised fleet, −{nm.cost_saving_vs_baseline_pct:.0f}% vs greedy"),
    ])

    body += section(4, "How the projects connect")
    body += ('<div class="flow">'
             '<a class="step" href="data.html"><b>0 · Clean data</b><span>1.55M rows → one validated layer</span></a>'
             '<a class="step" href="site-selection.html"><b>1 · Where?</b><span>FC network (p-median)</span></a>'
             '<a class="step" href="vrp.html"><b>2 · How?</b><span>Daily routes from the São Paulo FC</span></a>'
             '<a class="step" href="inventory.html"><b>3 · What?</b><span>Stock list & forecasts</span></a></div>')

    body += section(5, "Overall conclusion")
    body += callout(
        "<b>An FC network is a speed strategy, not a cost-saving one.</b> FCs cut distance in half and raise next-day reach "
        f"to {k3.pct_within_300km:.0f}%, but they save only ~R$ 3 of freight per item while inventory costs "
        f"~R$ {chosen.cost_per_unit_served:.0f} per unit. <b>Recommendation:</b> start with a São Paulo FC holding only the "
        "fast-moving products, deliver with a mixed fleet, and fund it through seller fulfilment fees (the Amazon FBA model). "
        "Add Rio and the Northeast as volume grows.")
    page("index.html", "Home", "From marketplace to fulfilment network: a supply-chain portfolio on 100k Olist orders.", body)


def build_data():
    log = pd.read_csv(PIPE / "cleaning_log.csv")
    rows = pd.read_csv(PIPE / "row_counts.csv")
    checks, rules = log[log.table == "validation"], log[log.table != "validation"]
    passed = int(checks.action.str.startswith("PASS").sum())
    body = hero("Project 0 · Data foundation", "One clean, validated dataset for every project",
                "The 9 raw Olist files are loaded untouched, then cleaned into typed, standardized and flagged tables in "
                "SQLite. Every rule is logged, and validation checks stop the run if a key rule breaks.",
                ["SQLite", "pandas", f"{len(rules)} logged rules", f"{passed}/{len(checks)} checks pass"])
    body += purpose("Can the raw data be trusted for network, routing and inventory decisions?",
                    "Turn messy raw files into one reliable layer, without silently losing information.",
                    "Clean tables, a cleaning log (every rule and row count) and automatic validation checks.",
                    "Every analysis in this portfolio, and any analyst who reuses the data.")
    body += kpis([("Source tables", "9", "1.55M raw rows"), ("Cleaning rules", len(rules), "each logged with row counts"),
                  ("Validation checks", f"{passed} / {len(checks)}", "keys, formats, coverage", "good"),
                  ("Valid delivered orders", "96,447", "the standard filter for logistics")])
    body += section(1, "Principles")
    body += cards([("🛡️", "Never delete silently", "Rows are dropped only if they are exact duplicates or physically "
                                                   "impossible. Questionable rows are kept with a flag column."),
                   ("📐", "Standardize once", "Types, ISO timestamps, 5-digit zip codes, one spelling per city, fixed column typos."),
                   ("✅", "Prove it", "Primary and foreign keys, formats, state codes and geo coverage are checked on every run.")])
    body += section(2, "Rows: raw vs clean", "Only geolocation loses rows; every business table keeps 100% of its rows")
    body += '<div class="chart" id="rows-chart"></div>'
    body += callout("Geolocation drops ~280k exact duplicates and 42 points outside Brazil. Problems in business tables, such "
                    "as 23 orders delivered before carrier pickup or 775 orders without items, are <b>flagged</b>, not deleted.", "insight")
    body += section(3, "Biggest fixes")
    body += cards([("🏙️", "City names", "Free-typed seller cities (<code>sbc/sp</code>, <code>lages - sc</code>, a zip code, "
                                        "an e-mail) are standardized or replaced with the zip code's city."),
                   ("📍", "Coordinates", "~38 points per zip are reduced to one median point; 162 missing zips are filled "
                                        "from their 3-digit region."),
                   ("🚩", "Order flags", "Impossible dates or orders without items are flagged. <code>is_valid_delivered</code> "
                                        "marks 96,447 trustworthy orders."),
                   ("📦", "Products", "610 missing categories → <code>unknown</code>, 6 missing weights → category median, "
                                     "the <code>lenght</code> typo fixed.")], cols=4)
    body += section(4, "Cleaning log", "Every rule, the rows it touched and the action taken")
    body += '<div class="controls"><div class="control"><label>Table</label><select id="log-filter"></select></div></div>'
    body += '<div class="table-wrap" id="log-table"></div>'
    body += section(5, "Validation checks")
    body += '<div class="table-wrap" id="check-table"></div>'
    data = {"rows": records(rows.assign(raw_rows=pd.to_numeric(rows.raw_rows, errors="coerce"))),
            "rules": records(rules), "checks": records(checks)}
    page("data.html", "Data cleaning", "How the raw Olist data was cleaned, logged and validated.", body, data, "data.js")


def build_site():
    s = pd.read_csv(SITE / "scenario_summary.csv")
    sites = pd.read_csv(SITE / "selected_sites.csv", dtype={"zone": str})
    assign = pd.read_csv(SITE / "zone_assignment.csv", dtype={"zone": str, "fc_zone": str})
    variants = pd.read_csv(SITE / "practical_variants_k3.csv")
    asis, k3 = s.iloc[0], s[s.k == 3].iloc[0]
    body = hero("Project 1 · Network design", "Where should Olist open fulfilment centres?",
                "Today every seller ships directly, so the average parcel travels ~775 km and takes 12 days. This project "
                "finds how many FCs to open, and where, to bring orders closer to customers.",
                ["p-median optimisation", "PuLP + HiGHS", "849 demand regions", "1–6 FC scenarios"])
    body += purpose("How many FCs should Olist open, and in which cities?",
                    "Minimise the distance between stock and customers, and show what each extra FC is worth.",
                    "A recommended network, a 1–6 FC trade-off curve, KPIs per scenario and a coverage map.",
                    "Network-strategy and real-estate teams, plus the leadership approving the FC investment.")
    body += callout("<b>Recommendation: open 3 FCs</b> (São Paulo, Minas Gerais/Rio corridor, Northeast). In practice: "
                    "<b>São Paulo + Rio + Salvador</b>, only 4% worse than the mathematical optimum and far easier to staff and supply.")
    body += kpis([("Avg distance to customer", f"{k3.avg_km:.0f} km", f"↓ 47% vs {asis.avg_km:.0f} km today", "good"),
                  ("Next-day reach (≤300 km)", f"{k3.pct_within_300km:.0f}%", f"↑ from {asis.pct_within_300km:.0f}% today", "good"),
                  ("Est. delivery time", f"{k3.est_delivery_days:.1f} days", f"↓ from {asis.est_delivery_days:.1f} days", "good"),
                  ("Est. freight per item", f"R$ {k3.est_freight_per_item:.2f}", f"↓ from R$ {asis.est_freight_per_item:.2f}", "good")])
    body += tabs([("results", "📊 Results & scenarios"), ("analysis", "🧭 Analysis: what we chose and why"), ("method", "⚙️ Method & data")])
    results = (section(1, "Pick a scenario", "Move the slider to see how the network and KPIs change with 1–6 FCs")
               + '<div class="controls"><div class="control"><label>Number of FCs</label>'
                 '<input type="range" id="k" min="1" max="6" value="3"><span class="range-val" id="k-val">3 FCs</span></div></div>'
               + '<div id="k-kpis"></div>'
               + section(2, "The network", "Each dot is a demand region (size = orders), coloured by the FC that serves it")
               + '<div class="cols"><div class="chart" id="map" style="height:540px"></div><div><div class="table-wrap" id="sites-table"></div>'
                 '<div id="fc-value"></div>'
               + callout("<b>Why Lagarto / Juiz de Fora?</b> The model picks the point closest to all the demand around it. "
                         "A business would choose the nearest big metro instead (section 4).", "insight") + "</div></div>"
               + section(3, "The trade-off: what each extra FC buys", "Dashed line = today; ringed point = selected scenario")
               + '<div class="chart" id="curves"></div>'
               + section(4, "Cost reality check", "Freight saved per extra FC, and the optimum vs. big-metro networks")
               + '<div class="cols even"><div class="chart" id="freight"></div><div><div class="table-wrap" id="variants-table"></div>'
               + callout("Big metros cost only ~4% more distance but bring workers, warehouses and carriers. "
                         "<b>Freight savings are small: the case for FCs is speed.</b>", "insight") + "</div></div>")
    method = (section("A", "Method") + """<div class="prose"><ol>
<li><b>Clean data:</b> valid delivered orders only; one median coordinate per zip code (project 0).</li>
<li><b>Demand regions (SQL):</b> orders grouped into 849 three-digit zip regions. <b>Candidates:</b> the top 3 regions per state + the top 60 nationally (119).</li>
<li><b>p-median model:</b> open exactly <i>k</i> sites, assign every region to one, and minimise order-weighted road distance (straight line × 1.3). Solved to proven optimality with PuLP + HiGHS for k = 1…6.</li>
<li><b>From km to KPIs:</b> regressions on ~110k real shipments. Delivery days ≈ 8.6 + 0.47 per 100 km (R² 0.18). Freight ≈ R$ 8.2 + 0.82 per 100 km + 2.58 per kg (R² 0.53).</li></ol>
<h3>Assumptions & limitations</h3><ul>
<li><b>Outbound only:</b> restocking FCs from sellers is not costed (76% of supply is already in São Paulo).</li>
<li><b>No FC fixed costs:</b> they are not in the data, so the break-even cost per FC is shown instead.</li>
<li><b>Estimated KPIs are directional</b> (R² 0.18 for days): use them to compare scenarios, not to promise an SLA.</li>
<li><b>No capacity limits;</b> historical demand (2017–18).</li></ul></div>"""
              + section("B", "All scenarios") + '<div class="table-wrap" id="all-table"></div>')
    body += panel("results", results, True) + panel("analysis", analysis(ROOT / "site_selection" / "ANALYSIS.md")) + panel("method", method)
    data = {"summary": records(s), "sites": records(sites), "variants": records(variants),
            "assign": records(assign[["k", "zone", "state", "orders", "lat", "lng", "fc_zone", "road_km"]])}
    page("site-selection.html", "Site selection", "How many fulfilment centres should Olist open, and where?", body, data, "site-selection.js")


def build_vrp():
    sc = pd.read_csv(VRP / "vrp_scenarios.csv")
    routes = pd.read_csv(VRP / "vrp_routes.csv")
    depot = pd.read_csv(VRP / "depot.csv").iloc[0]
    cities = pd.read_csv(VRP / "orders_by_city.csv")
    a = pd.read_csv(VRP / "vrp_assumptions.csv")
    r = sc.set_index("scenario")
    nm, bm, bf = r.loc["normal__mixed"], r.loc["black_friday__mixed"], r.loc["black_friday__normal_fleet"]
    body = hero("Project 2 · Last-mile delivery", "How should the São Paulo FC deliver every day?",
                f"Daily routes from the FC chosen in project 1 to customers across Grande São Paulo. A normal day "
                f"({int(nm.orders)} orders) is compared with Black Friday 2017 ({int(bm.orders)} orders), using vans, "
                "motorbikes or a mix of both.", ["Vehicle routing (CVRP)", "Google OR-Tools", "7 scenarios", "Grande São Paulo, 11–23 cities"])
    body += purpose("How many vehicles, which type, at what cost per delivery, and what happens on a peak day?",
                    "Deliver every order within one shift at the lowest cost, and size the extra capacity a peak needs.",
                    "Optimised routes per vehicle, fleet size and mix, cost per order and the peak-day capacity gap.",
                    "Last-mile operations and fleet managers, and capacity planners preparing for Black Friday.")
    body += callout(f"<b>Recommendation: run a mixed fleet (vans + motorbikes) and contract extra riders for peaks.</b> "
                    f"A normal day needs 2 vans + 2 motorbikes at <b>R$ {nm.cost_per_order:.2f}</b> per order. With only that fleet, "
                    f"<b>{int(bf.orders_not_delivered)} of {int(bf.orders)}</b> Black Friday orders would be a day late.")
    body += kpis([("Normal-day fleet", f"{int(nm.vans)} vans + {int(nm.motorbikes)} motos", f"{int(nm.orders)} orders, all delivered"),
                  ("Cost per order", f"R$ {nm.cost_per_order:.2f}", f"↓ {nm.cost_saving_vs_baseline_pct:.0f}% vs greedy plan", "good"),
                  ("Black Friday fleet", f"{int(bm.vans + bm.motorbikes)} vehicles", f"{int(bm.vans)} vans + {int(bm.motorbikes)} motos"),
                  ("Peak gap (normal fleet)", f"{bf.orders_not_delivered / bf.orders * 100:.0f}% late", f"{int(bf.orders_not_delivered)} orders slip a day", "bad")])
    body += tabs([("results", "📊 Results & routes"), ("analysis", "🧭 Analysis: what we chose and why"), ("method", "⚙️ Method & data")])
    results = (section(1, "Pick a day and a fleet", "Every combination was solved separately with OR-Tools")
               + '<div class="controls"><div class="control"><label>Day</label><div class="seg" id="day"></div></div>'
                 '<div class="control"><label>Fleet</label><div class="seg" id="fleet"></div></div></div><div id="s-kpis"></div>'
               + section(2, "The routes", "Each line is one vehicle's round trip from the FC; hover a stop for its sequence and arrival time")
               + '<div class="cols"><div class="chart" id="map" style="height:520px"></div><div><div class="table-wrap" id="routes-table"></div>'
               + callout("Vans are limited by <b>time</b> (load far below 100%), motorbikes by <b>box volume</b>.", "insight") + "</div></div>"
               + section(3, "Which fleet is cheapest?", "Cost per delivered order for each fleet, on both days")
               + '<div class="chart" id="cost"></div>'
               + callout(f"<b>Mixed wins on both days.</b> Motorbike-only looks cheap but leaves "
                         f"{int(r.loc['normal__motorbike_only'].orders_too_big_for_fleet)} bulky orders undelivered. With 4× the orders, "
                         f"cost per order <i>falls</i> (R$ {nm.cost_per_order:.2f} → R$ {bm.cost_per_order:.2f}) because stops are denser.", "insight")
               + section(4, "Where the orders go", "The service area is the whole metro region, not only São Paulo city")
               + '<div class="table-wrap" id="cities-table"></div>')
    av = a[a.vehicle_type != "shift"]
    rows_html = "".join(f"<tr><td>{x.vehicle_type.title()}</td><td class=num>{x.weight_kg:.0f} kg</td><td class=num>{x.volume_l:,.0f} L</td>"
                        f"<td class=num>{x.speed_kmh:.0f} km/h</td><td class=num>{x.service_min:.0f} min</td>"
                        f"<td class=num>R$ {x.cost_per_km:.2f}</td><td class=num>R$ {x.cost_per_day:.0f}</td></tr>" for x in av.itertuples())
    method = (section("A", "Method") + """<div class="prose"><p><b>Model.</b> A capacitated vehicle routing problem with a 9-hour shift
limit and a mixed fleet. Every order is visited once; every vehicle respects its weight, volume and time limits. The objective is to minimise
(cost per vehicle-day) + (cost per km), solved with <b>Google OR-Tools</b> (guided local search). The mixed-fleet search starts from the
van-only plan, so it can only match or beat it.</p><p><b>Data.</b> Valid delivered orders for customers in Grande São Paulo (zip 01000–09999),
with weight and volume from the product data.</p><h3>Assumptions (illustrative)</h3>
<table><thead><tr><th>Vehicle</th><th class=num>Max weight</th><th class=num>Max volume</th><th class=num>Speed</th><th class=num>Per stop</th>
<th class=num>Per km</th><th class=num>Per day</th></tr></thead><tbody>""" + rows_html + """</tbody></table>
<ul><li>One shift = 9 hours, FC to FC. Orders bought on day D are delivered on day D+1.</li>
<li>Distance = straight line × 1.3; customer location = zip-code centroid.</li>
<li>No traffic or customer time windows; results vary ±1–2% between runs (solver time limit), the fleet ranking is stable.</li></ul></div>"""
              + section("B", "All scenarios") + '<div class="table-wrap" id="all-table"></div>')
    body += panel("results", results, True) + panel("analysis", analysis(ROOT / "vrp" / "ANALYSIS.md")) + panel("method", method)
    data = {"scenarios": records(sc.drop(columns=["fleet_bound_reached"], errors="ignore")),
            "routes": records(routes[["scenario", "route", "vehicle_type", "seq", "order_id", "city", "lat", "lng",
                                      "arrival_min", "route_km", "route_min", "volume_util_pct"]].assign(
                                          order_id=lambda d: (d.order_id != "FC").astype(int)), digits=4),
            "depot": {"lat": float(depot.lat), "lng": float(depot.lng)}, "cities": records(cities)}
    page("vrp.html", "Vehicle routing", "Daily last-mile routes from the São Paulo FC: vans vs motorbikes, normal day vs Black Friday.",
         body, data, "vrp.js")


def build_inventory():
    t = pd.read_csv(INV / "policy_tradeoff.csv")
    chosen = t[(t.sweep == "stock_rule") & (t.stock_rule_min_weeks == 6)].iloc[0]
    body = hero("Project 3 · Inventory policy", "What should the São Paulo FC stock, and how much?",
                "About 19,000 different products reached the FC's area in one year, and most sell only once or twice. This "
                "project decides which products to hold, how many and when to reorder, compares 16 forecast methods, and "
                "tests the policy day by day on 16 unseen weeks.",
                ["ABC × demand pattern", "SES · Holt · Holt-Winters · Croston · TSB", "Reorder point + EOQ", "Day-by-day simulation"])
    body += purpose("Which products should the FC hold, how many of each, and when should it reorder?",
                    "Ship as many units as possible from FC stock while keeping capital, space and cost under control.",
                    "A stock list with reorder points, service-level and assortment trade-offs, a forecast comparison and a tested policy.",
                    "Inventory planners and category managers, plus the finance team that funds the stock.")
    body += callout(f"<b>Recommendation: stock only the ~{int(chosen.products_listed_last_week)} most regular products</b> (sold in "
                    "≥6 of the last 12 weeks), forecast them with exponential smoothing, <b>re-plan every Monday</b> and target 95%. "
                    "Sellers keep shipping everything else directly.")
    body += kpis([("Products in the FC", int(chosen.products_listed_last_week), "of ~19,000 sold in the area"),
                  ("Units shipped from FC", f"{chosen.fc_share_of_all_units_pct:.1f}%", "rest shipped by sellers"),
                  ("Fill rate", f"{chosen.fill_rate_pct:.1f}%", "on stocked products"),
                  ("Average stock", f"R$ {chosen.avg_inventory_value / 1000:.0f}k", f"{chosen.weeks_of_cover:.1f} weeks of cover · {chosen.avg_space_m3:.0f} m³"),
                  ("Cost per unit", f"R$ {chosen.cost_per_unit_served:.2f}", "holding + orders + returns")])
    body += callout("<b>Key finding:</b> 52% of units sold in the test weeks came from products with <b>no sales at all</b> in the "
                    "previous 34 weeks. Volume is stable but the products keep changing, so the plan is rebuilt every Monday.", "insight")
    body += tabs([("results", "📊 Results & trade-offs"), ("analysis", "🧭 Analysis: what we chose and why"), ("method", "⚙️ Method & data")])
    results = (section(1, "Explore the trade-offs", "Pick a decision; the dark bar is the recommended policy")
               + '<div class="controls"><div class="control"><label>Decision</label><div class="seg" id="sweep"></div></div></div>'
                 '<div class="chart" id="sweep-chart"></div><div id="sweep-note"></div><div id="static-note"></div>'
               + section(2, "Which products qualify?", "A very long tail: few products sell regularly")
               + '<div class="cols even"><div class="chart" id="curve"></div><div><p id="tail-note"></p>'
                 '<div class="table-wrap" id="matrix-table"></div><p class="caption">Products by ABC class (revenue, A = top 80%) × '
                 'Syntetos-Boylan demand pattern. <i>Intermittent</i> = does not sell every week.</p></div></div>'
               + section(3, "The plan: reorder points per product", "The list as it stood on the last Monday of the test")
               + '<div class="controls"><div class="control"><label>Category</label><select id="cat"></select></div></div>'
                 '<div class="table-wrap" id="plan-table"></div><p class="caption">How to read a row: when stock on hand + on order '
                 'falls to <i>Reorder at</i>, order <i>Order qty</i> units from the seller.</p>'
               + section(4, "Which forecast method?", "Compared at two levels: per product (drives stock) and FC total per day (drives staffing)")
               + '<div class="controls"><div class="control"><label>Level</label><div class="seg" id="level"></div></div></div>'
                 '<div id="fc-product"><div class="chart" id="fc-chart"></div><div id="fc-note"></div></div>'
                 '<div id="fc-daily" style="display:none"><div class="cols even"><div class="chart" id="daily-bars"></div>'
                 '<div class="chart" id="daily-line"></div></div><div id="daily-note"></div></div>')
    method = (section("A", "Method") + """<div class="prose"><ul>
<li><b>Demand:</b> valid delivered items from customers in the zones served by the São Paulo FC (project 1). Calibration Sep 2017–Apr 2018 (34 weeks), test May–Aug 2018 (16 weeks).</li>
<li><b>Weekly plan (Mondays, past data only):</b> stock list = sold in ≥6 of the last 12 weeks; forecast = exponential smoothing (SES); safety stock = z × σ(weekly demand) × √(lead time / 7); reorder point = lead-time demand + safety stock; order quantity = min(EOQ, 8 weeks of demand).</li>
<li><b>Simulation:</b> real daily orders with 4 warm-up weeks. Unserved demand is shipped by the seller (no lost sale); stock of delisted products is returned to the seller.</li>
<li><b>Forecast backtests:</b> 7 methods per product per week (scored on error <i>and</i> on the stock outcome) and 9 methods for the FC's daily total (7-day-ahead rolling, incl. Holt-Winters).</li></ul>
<h3>Assumptions</h3><table><thead><tr><th>Assumption</th><th>Value</th></tr></thead><tbody>
<tr><td>Lead time</td><td>seller handling (data, median ≈ 2 days) + 2 days transit + 1 day receiving ≈ 6 days</td></tr>
<tr><td>Holding cost</td><td>25% of product value per year</td></tr>
<tr><td>Replenishment / removal order</td><td>R$ 40 each</td></tr><tr><td>Unit value</td><td>customer price</td></tr></tbody></table></div>"""
              + section("B", "All simulated policies") + '<div class="table-wrap" id="all-table"></div>')
    body += panel("results", results, True) + panel("analysis", analysis(ROOT / "inventory" / "ANALYSIS.md")) + panel("method", method)
    matrix = pd.read_csv(INV / "abc_pattern_matrix.csv", index_col=0)
    data = {"tradeoff": records(t.astype({"order_cap_weeks": str})),
            "seg": json.loads(pd.read_csv(INV / "segmentation_summary.csv").iloc[0].to_json()),
            "matrix": {"index": matrix.index.tolist(), "columns": matrix.columns.tolist(), "values": matrix.to_numpy().tolist()},
            "curve": records(pd.read_csv(INV / "sku_coverage_curve.csv")),
            "fc": records(pd.read_csv(INV / "forecast_backtest.csv")),
            "plan": records(pd.read_csv(INV / "policy_by_product.csv").drop(columns=["product_id"])),
            "daily": records(pd.read_csv(INV / "forecast_daily_backtest.csv")),
            "dailySeries": records(pd.read_csv(INV / "forecast_daily_series.csv")),
            "weekday": json.loads(pd.read_csv(INV / "weekday_index.csv", index_col=0)["index"].to_json())}
    page("inventory.html", "Inventory", "What the São Paulo FC should stock: segmentation, forecasting and a tested reorder policy.",
         body, data, "inventory.js")


if __name__ == "__main__":
    print("Building docs/ ...")
    build_home(); build_data(); build_site(); build_vrp(); build_inventory()
    (DOCS / ".nojekyll").write_text("")          # serve files as-is on GitHub Pages
    print("Done. Open docs/index.html or push to GitHub Pages.")
