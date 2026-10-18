"""Data foundation - what was cleaned, why, and the validation results."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_common import MUTED, SERIES, load_report, setup_page

setup_page("Data Cleaning", "🧹")

st.title("0 · Data foundation")
st.markdown(
    "Every project reads the same **clean layer**, never the raw CSVs. The pipeline loads the 9 raw files "
    "untouched (`raw_*` tables), then builds typed, standardized and flagged tables in SQLite. "
    "**Every rule is logged, and validation checks stop the run if a key rule breaks.**"
)

log = load_report("cleaning_log")
rows = load_report("row_counts")
checks = log[log.table == "validation"]
rules = log[log.table != "validation"]
passed = checks.action.str.startswith("PASS").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Source tables", "9")
c2.metric("Cleaning rules logged", len(rules))
c3.metric("Validation checks passed", f"{passed} / {len(checks)}")
c4.metric("Valid delivered orders", "96,447", help="orders.is_valid_delivered = 1: the standard filter for logistics analyses")

st.subheader("Principles")
p1, p2, p3 = st.columns(3)
p1.info("**Never delete silently.** Rows are dropped only if they are exact duplicates or physically impossible. "
        "Questionable rows are kept with a flag column.")
p2.info("**Standardize once.** Types, ISO timestamps, 5-digit zip codes, one spelling per city, fixed column-name typos.")
p3.info("**Prove it.** Primary and foreign keys, formats, state codes and geo coverage are checked on every run.")

st.subheader("Rows: raw vs clean")
r = rows[rows.table != "geo_zip_centroid"].copy()
r["raw_rows"] = r.raw_rows.astype(float)
r["removed"] = r.raw_rows - r.clean_rows
st.caption("Only geolocation loses rows (duplicates and points outside Brazil). Every business table keeps 100% of its rows; "
           "problems are flagged instead.")
fig = go.Figure()
fig.add_bar(y=r.table, x=r.clean_rows, name="Kept", orientation="h", marker_color=SERIES[0],
            hovertemplate="%{y}: %{x:,} rows kept<extra></extra>")
fig.add_bar(y=r.table, x=r.removed.clip(lower=0), name="Removed", orientation="h", marker_color=MUTED,
            hovertemplate="%{y}: %{x:,} rows removed<extra></extra>")
fig.update_layout(barmode="stack", height=330, margin=dict(l=0, r=0, t=10, b=0), xaxis_type="log",
                  xaxis_title="Rows (log scale)", legend=dict(orientation="h", y=1.08, x=0), bargap=0.35)
st.plotly_chart(fig, width="stretch")

st.subheader("Cleaning log")
tables = ["All"] + sorted(rules.table.unique())
pick = st.segmented_control("Table", tables, default="All", label_visibility="collapsed")
view = rules if pick in (None, "All") else rules[rules.table == pick]
st.dataframe(
    view.rename(columns={"table": "Table", "rule": "Issue / rule", "rows_affected": "Rows", "action": "Action"}),
    hide_index=True, width="stretch",
    column_config={"Rows": st.column_config.NumberColumn(format="%d")},
)

st.subheader("Validation checks")
st.dataframe(
    pd.DataFrame({"Check": checks.rule, "Result": checks.action.str.strip()}),
    hide_index=True, width="stretch",
)

with st.expander("Examples of standardized seller cities"):
    st.markdown(
        """
| Raw value | Clean value | Rule |
|---|---|---|
| `sao paulo / sao paulo` | `sao paulo` | tail after `/` removed |
| `lages - sc` | `lages` | state suffix removed |
| `novo hamburgo, rio grande do sul, brasil` | `novo hamburgo` | tail after `,` removed |
| `sbc/sp` | `sao bernardo do campo` | not a known city, so the zip code's city is used |
| `floranopolis` | `florianopolis` | typo, so the zip code's city is used |
| `04482255` | `rio de janeiro` | a zip code typed as the city |
| `são paulo` | `sao paulo` | accents removed |
| `embu-guaçu` | `embu-guacu` | official hyphen kept |
"""
    )

with st.expander("Why no columns were dropped as 'empty'"):
    st.markdown(
        "No column in the dataset is 100% empty. Columns with partial nulls still carry information, so their gaps are "
        "**flagged or imputed** (e.g. 610 products without a category become `unknown`; 6 products without a weight get "
        "their category's median). The only columns dropped are the two Portuguese free-text review comments "
        "(88% and 59% empty), which no supply-chain analysis uses."
    )
