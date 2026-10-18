"""Home page - the research purpose, the three questions, their answers and how they connect."""
import streamlit as st

from app_common import callout, hero, info_cards, kpis, load_site, section, setup_page

# Edit these to your own profile links
AUTHOR = "Razka"
LINKS = {"GitHub": "https://github.com/razka300905-ctrl/olist-supply-chain", "LinkedIn": ""}

setup_page("Home", "📦")

summary = load_site("scenario_summary")
asis, k3 = summary.iloc[0], summary[summary.k == 3].iloc[0]

hero(
    "Supply chain portfolio · Olist, Brazil · by " + AUTHOR,
    "From marketplace to fulfilment network",
    "An end-to-end study on ~100k real e-commerce orders. It asks how Olist could deliver faster by running its own "
    "fulfilment centres: <b>where</b> to put them, <b>how</b> to deliver from them, and <b>what</b> to stock in them.",
    ["Python", "SQL", "Optimisation (MILP · OR-Tools)", "Forecasting", "Simulation", "Streamlit"],
)
links = " · ".join(f"[{k}]({v})" for k, v in LINKS.items() if v)
if links:
    st.markdown(links)

# ------------------------------------------------------------------ 1. purpose
section(1, "Why this research?", "The problem, the objective and what the research delivers")
info_cards([
    ("🚚", "The problem",
     "Olist is a marketplace: <b>every seller ships directly</b> to the customer. 76% of items leave São Paulo state, "
     "but only 42% of orders go there, so the average parcel travels <b>~775 km</b> and takes <b>12 days</b>."),
    ("🎯", "The objective",
     "Design a <b>fulfilment-centre (FC) model</b> end to end, and quantify its trade-offs in service, cost and capital. "
     "The result should support a real go / no-go discussion, not just show a model."),
    ("❓", "The main question",
     "<b>Should Olist run its own FC network, and if so, how?</b> It splits into three linked decisions: "
     "where (network), how (delivery) and what (stock)."),
], cols=3)
info_cards([
    ("📦", "Outputs",
     "A recommended FC network · daily delivery routes and fleet mix · a stock list with reorder points · "
     "trade-off curves · an interactive app · reproducible Python + SQL code."),
    ("👥", "Who it is for",
     "Supply-chain and operations leaders deciding on network, fleet and inventory. Product managers building "
     "fulfilment services for sellers."),
    ("🧭", "How to read it",
     "Each project page follows the same order: <b>purpose → answer → results → analysis → method</b>. "
     "Start with project 0 (data) or jump straight to the answers below."),
], cols=3)

# ------------------------------------------------------------------ 2. questions and answers
section(2, "Three questions, three answers", "Each project answers one decision and feeds the next")
c = st.columns(3)
answers = [
    ("📍 1 · Where?", "How many FCs, and where?",
     f"<b>3 FCs</b>: São Paulo, Minas Gerais/Rio, Northeast. Distance <b>−47%</b>, next-day reach "
     f"<b>{asis.pct_within_300km:.0f}% → {k3.pct_within_300km:.0f}%</b>.", "app_pages/site_selection.py"),
    ("🚚 2 · How?", "How should the São Paulo FC deliver every day?",
     "<b>Mixed fleet</b> (vans + motorbikes): R$ 23 per order on a normal day. Black Friday needs <b>~4×</b> the "
     "vehicles.", "app_pages/vrp.py"),
    ("📦 3 · What?", "What should the FC stock, and how much?",
     "<b>~130 regular products</b>, re-planned weekly at a 95% service level: 13% of units from FC stock, "
     "R$ 139k of inventory.", "app_pages/inventory.py"),
]
for col, (eyebrow, q, a, page) in zip(c, answers):
    with col:
        info_cards([("", eyebrow, f"<i>{q}</i><br><br>{a}")], cols=1, min_height=210)
        st.page_link(page, label="Open the project →")

# ------------------------------------------------------------------ 3. headline numbers
section(3, "Headline numbers")
kpis([
    {"label": "Orders analysed", "value": "99,441", "note": "2016–2018, all of Brazil"},
    {"label": "Data cleaned", "value": "1.55M rows", "note": "9 tables · 17 checks pass"},
    {"label": "Avg distance (3 FCs)", "value": f"{k3.avg_km:.0f} km", "note": f"−47% vs {asis.avg_km:.0f} km today", "tone": "good"},
    {"label": "Next-day reach", "value": f"{k3.pct_within_300km:.0f}%", "note": f"+{k3.pct_within_300km - asis.pct_within_300km:.0f} pp vs today", "tone": "good"},
    {"label": "Cost per delivery", "value": "R$ 23", "note": "optimised mixed fleet, −28% vs greedy"},
])

# ------------------------------------------------------------------ 4. conclusion
section(4, "Overall conclusion")
callout(
    "<b>An FC network is a speed strategy, not a cost-saving one.</b> FCs cut distance in half and raise next-day "
    "reach to 58%, but they save only ~R$ 3 of freight per item while inventory costs ~R$ 17 per unit. "
    "<b>Recommendation:</b> start with a São Paulo FC holding only the fast-moving products, deliver with a mixed "
    "fleet, and fund it through seller fulfilment fees (the Amazon FBA model). Add Rio and the Northeast as volume grows.",
    "recommend",
)
st.markdown(
    """
```
Raw CSVs ─► 0 · Data cleaning ─► 1 · Where? (FC network) ─► 2 · How? (delivery routes) ─► 3 · What? (stock)
                                   São Paulo FC = depot ───────┘          São Paulo FC = stock point ─┘
```
"""
)
st.caption("Data: Olist Brazilian E-Commerce Public Dataset (Kaggle, CC BY-NC-SA 4.0). Costs, speeds and capacities "
           "that are not in the data are clearly marked assumptions on each page.")
