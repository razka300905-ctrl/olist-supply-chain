"""Data foundation - what was cleaned, why, and the validation results."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_common import MUTED, SERIES, callout, hero, info_cards, kpis, load_report, purpose, section, setup_page, style_fig

setup_page("Data Cleaning", "🧹")

log = load_report("cleaning_log")
rows = load_report("row_counts")
checks = log[log.table == "validation"]
rules = log[log.table != "validation"]
passed = checks.action.str.startswith("PASS").sum()

hero("Project 0 · Data foundation",
     "One clean, validated dataset for every project",
     "The 9 raw Olist files are loaded untouched, then cleaned into typed, standardized and flagged tables in SQLite. "
     "Every rule is logged, and validation checks stop the run if a key rule breaks.",
     ["SQLite", "pandas", f"{len(rules)} logged rules", f"{passed}/{len(checks)} checks pass"])

purpose(
    "Can the raw data be trusted for network, routing and inventory decisions?",
    "Turn messy raw files into one reliable layer, without silently losing information.",
    "Clean tables, a cleaning log (every rule and row count) and automatic validation checks.",
    "Every analysis in this portfolio, and any analyst who reuses the data.",
)

kpis([
    {"label": "Source tables", "value": "9", "note": "1.55M raw rows"},
    {"label": "Cleaning rules", "value": len(rules), "note": "each logged with row counts"},
    {"label": "Validation checks", "value": f"{passed} / {len(checks)}", "note": "keys, formats, coverage", "tone": "good"},
    {"label": "Valid delivered orders", "value": "96,447", "note": "the standard filter for logistics"},
])

tab_res, tab_m = st.tabs(["📊  What was cleaned", "⚙️  Rules, log & checks"])

with tab_res:
    section(1, "Principles")
    info_cards([
        ("🛡️", "Never delete silently", "Rows are dropped only if they are exact duplicates or physically impossible. "
                                        "Questionable rows are kept with a flag column."),
        ("📐", "Standardize once", "Types, ISO timestamps, 5-digit zip codes, one spelling per city, fixed column-name typos."),
        ("✅", "Prove it", "Primary and foreign keys, formats, state codes and geo coverage are checked on every run."),
    ])

    section(2, "Rows: raw vs clean", "Only geolocation loses rows; every business table keeps 100% of its rows")
    r = rows[rows.table != "geo_zip_centroid"].copy()
    r["raw_rows"] = r.raw_rows.astype(float)
    r["removed"] = r.raw_rows - r.clean_rows
    fig = go.Figure()
    fig.add_bar(y=r.table, x=r.clean_rows, name="Kept", orientation="h", marker_color=SERIES[0],
                hovertemplate="%{y}: %{x:,} rows kept<extra></extra>")
    fig.add_bar(y=r.table, x=r.removed.clip(lower=0), name="Removed", orientation="h", marker_color=MUTED,
                hovertemplate="%{y}: %{x:,} rows removed<extra></extra>")
    fig.update_layout(barmode="stack", xaxis_type="log", xaxis_title="Rows (log scale)",
                      legend=dict(orientation="h", y=1.1, x=0), bargap=0.35)
    st.plotly_chart(style_fig(fig, 340), width="stretch")
    callout("Geolocation drops ~280k exact duplicates and 42 points outside Brazil. Problems in business tables, such as "
            "23 orders delivered before carrier pickup or 775 orders without items, are <b>flagged</b>, not deleted.", "insight")

    section(3, "Biggest fixes")
    info_cards([
        ("🏙️", "City names", "Seller cities typed freely (<code>sbc/sp</code>, <code>lages - sc</code>, a zip code, an e-mail) "
                            "are standardized, or replaced with the zip code's city."),
        ("📍", "Coordinates", "~38 points per zip code are reduced to one median point. 162 missing zips are filled from "
                             "their 3-digit region."),
        ("🚩", "Order flags", "Orders with impossible dates or no items are flagged. <code>is_valid_delivered</code> marks "
                             "96,447 trustworthy orders."),
        ("📦", "Products", "610 missing categories become <code>unknown</code>, 6 missing weights get the category median, "
                          "and the <code>lenght</code> typo is fixed."),
    ], cols=4)
    callout("<b>Why no columns were dropped as \"empty\":</b> no column is 100% empty. Partial gaps are flagged or imputed. "
            "Only the two Portuguese free-text review comments (88% and 59% empty) were dropped, since no supply-chain "
            "analysis uses them.", "note")

with tab_m:
    section("A", "Cleaning log", "Every rule, the rows it touched, and the action taken")
    tables = ["All"] + sorted(rules.table.unique())
    pick = st.segmented_control("Table", tables, default="All", label_visibility="collapsed")
    view = rules if pick in (None, "All") else rules[rules.table == pick]
    st.dataframe(view.rename(columns={"table": "Table", "rule": "Issue / rule", "rows_affected": "Rows", "action": "Action"}),
                 hide_index=True, width="stretch", column_config={"Rows": st.column_config.NumberColumn(format="%d")})

    section("B", "Validation checks")
    st.dataframe(pd.DataFrame({"Check": checks.rule, "Result": checks.action.str.strip()}), hide_index=True, width="stretch")

    section("C", "Examples of standardized seller cities")
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
