"""Home page - portfolio overview."""
import streamlit as st

from app_common import load_report, load_site, setup_page

# Edit these to your own profile links
AUTHOR = "Razka"
LINKS = {"GitHub": "", "LinkedIn": ""}

setup_page("Home", "📦")

st.title("Olist Supply Chain Portfolio")
st.markdown(
    f"**By {AUTHOR}.** Three end-to-end supply-chain case studies on real Brazilian e-commerce data. "
    "Each one frames a business decision, builds the model in **Python + SQL**, and ends with a "
    "recommendation and its trade-offs, the way a Supply Chain Product Manager would present it."
)
links = " · ".join(f"[{k}]({v})" for k, v in LINKS.items() if v)
if links:
    st.markdown(links)

summary = load_site("scenario_summary")
asis, k3 = summary.iloc[0], summary[summary.k == 3].iloc[0]
rows = load_report("row_counts")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Orders analysed", "99,441", help="All orders in the Olist dataset, 2016–2018")
c2.metric("Raw rows cleaned", f"{int(rows.raw_rows.replace('-', 0).astype(float).sum()):,}")
c3.metric("Avg. distance with 3 FCs", f"{k3.avg_km:.0f} km", f"{(k3.avg_km / asis.avg_km - 1) * 100:.0f}% vs today",
          delta_color="inverse")
c4.metric("Next-day reach with 3 FCs", f"{k3.pct_within_300km:.0f}%",
          f"+{k3.pct_within_300km - asis.pct_within_300km:.0f} pp vs today")

st.divider()
st.subheader("Projects")

p0, p1, p2, p3 = st.columns(4)
with p0:
    with st.container(border=True):
        st.markdown("#### 0 · Data foundation")
        st.caption("✅ Done")
        st.write("A logged, validated cleaning pipeline that turns 9 raw CSVs into analysis-ready tables, "
                 "shared by every project.")
        st.page_link("app_pages/data_cleaning.py", label="Open data cleaning →")
with p1:
    with st.container(border=True):
        st.markdown("#### 1 · Site selection")
        st.caption("✅ Done")
        st.write("How many fulfilment centres should Olist open, and where? A p-median model "
                 "for 1–6 sites, with service-level and freight trade-offs.")
        st.page_link("app_pages/site_selection.py", label="Open site selection →")
with p2:
    with st.container(border=True):
        st.markdown("#### 2 · Vehicle routing")
        st.caption("✅ Done")
        st.write("Daily last-mile routes from the São Paulo FC: vans vs motorbikes, normal day vs "
                 "Black Friday, solved with OR-Tools.")
        st.page_link("app_pages/vrp.py", label="Open vehicle routing →")
with p3:
    with st.container(border=True):
        st.markdown("#### 3 · Inventory")
        st.caption("⏳ Next")
        st.write("How much stock each FC should hold: demand forecasting, safety stock and "
                 "service level against holding cost.")

st.divider()
st.subheader("How the projects connect")
st.markdown(
    """
```
Raw CSVs ─► Data cleaning ─► Site selection ─► Vehicle routing ─► Inventory
                              (where are FCs?)   (FCs = depots)     (FCs = stock points)
```
"""
)
st.caption("Data: Olist Brazilian E-Commerce Public Dataset (Kaggle, CC BY-NC-SA 4.0). "
           "Built with Python, SQLite, PuLP/HiGHS, pandas, Plotly and Streamlit.")
