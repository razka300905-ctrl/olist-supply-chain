"""Shared helpers for the Streamlit portfolio app: paths, palette, cached loaders and the UI kit
(hero banner, purpose cards, KPI cards, callouts, section headers, chart styling)."""
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SITE_OUT = ROOT / "site_selection" / "outputs"
SITE_FIG = ROOT / "site_selection" / "figures"
PIPE_REPORTS = ROOT / "data_pipeline" / "reports"

# Categorical palette, fixed order (validated reference palette)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MUTED = "#898781"
LIGHT_BLUE = "#b7d3f6"
# Colour follows the hub's region so a hub keeps its colour for every k (same rule as the static maps)
REGION_SLOT = {"SP": 0, "SE": 1, "AL": 1, "BA": 1, "PE": 1, "MG": 2, "RS": 3, "GO": 4, "DF": 4, "RJ": 5}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, .stMarkdown, button, input, textarea, select { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.block-container { padding-top: 3.4rem; padding-bottom: 4rem; max-width: 1220px; }
h1, h2, h3 { letter-spacing: -0.01em; }
.stMarkdown h2 { font-size: 1.45rem; font-weight: 700; margin-top: 1.6rem; }
.stMarkdown h3 { font-size: 1.12rem; font-weight: 700; margin-top: 1.2rem; }

/* hero banner */
.hero { background: linear-gradient(135deg, #0d3a75 0%, #2a78d6 58%, #1baf7a 135%); border-radius: 20px;
        padding: 34px 38px 30px; color: #fff; margin: 0 0 20px; box-shadow: 0 12px 32px rgba(13, 58, 117, .18); }
.hero .eyebrow { font-size: .76rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 700; opacity: .85; }
.hero h1 { color: #fff; font-size: 2.15rem; line-height: 1.18; font-weight: 800; margin: .4rem 0 .6rem; padding: 0; }
.hero p { font-size: 1.04rem; line-height: 1.55; opacity: .93; max-width: 860px; margin: 0; color: #fff; }
.chips { margin-top: 18px; display: flex; gap: 8px; flex-wrap: wrap; }
.chip { background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3); padding: 4px 12px;
        border-radius: 999px; font-size: .78rem; font-weight: 600; color: #fff; }

/* cards */
.grid { display: grid; gap: 14px; margin: 6px 0 20px; }
.grid.c2 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
.grid.c3 { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.grid.c4 { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
.grid.c5 { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
.card { background: #fff; border: 1px solid #e6e5df; border-radius: 16px; padding: 18px 18px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 6px 16px rgba(0,0,0,.04); }
.card .label { font-size: .74rem; color: #6b6a65; text-transform: uppercase; letter-spacing: .07em; font-weight: 700; }
.card .value { font-size: 1.7rem; font-weight: 800; color: #0b0b0b; margin: .3rem 0 .2rem; line-height: 1.15; }
.card .note { font-size: .84rem; color: #52514e; line-height: 1.4; }
.card .note.good { color: #006300; font-weight: 600; }
.card .note.bad { color: #b42318; font-weight: 600; }
.card .icon { font-size: 1.35rem; line-height: 1; }
.card .title { font-weight: 700; font-size: 1rem; margin: .45rem 0 .3rem; color: #0b0b0b; }
.card .body { font-size: .9rem; color: #3d3c39; line-height: 1.5; }
.card.accent { border-top: 4px solid #2a78d6; }

/* callouts */
.callout { border-radius: 14px; padding: 16px 18px; margin: 6px 0 20px; border: 1px solid; display: flex; gap: 14px;
           align-items: flex-start; font-size: .97rem; line-height: 1.55; color: #1f1f1d; }
.callout .ci { font-size: 1.3rem; line-height: 1.3; }
.callout.recommend { background: #eef5fd; border-color: #bcd6f5; }
.callout.insight { background: #fff7e6; border-color: #f3d79b; }
.callout.note { background: #f4f4f1; border-color: #e1e0d9; }

/* numbered section headers */
.section { display: flex; align-items: center; gap: 12px; margin: 30px 0 4px; }
.section .num { flex: none; width: 30px; height: 30px; border-radius: 9px; background: #2a78d6; color: #fff;
                font-weight: 800; display: flex; align-items: center; justify-content: center; font-size: .9rem; }
.section .stitle { font-size: 1.32rem; font-weight: 800; color: #0b0b0b; }
.ssub { color: #52514e; font-size: .95rem; margin: 2px 0 12px 42px; }

/* streamlit widgets */
.stTabs [role="tablist"] { gap: 4px; border-bottom: 1px solid #e6e5df; }
.stTabs [role="tab"] { height: 50px; padding: 0 20px; border-radius: 10px 10px 0 0; }
.stTabs [role="tab"] p, .stTabs [role="tab"] div { font-size: 1.02rem !important; font-weight: 700 !important; }
.stTabs [role="tabpanel"] { padding-top: 6px; }
.stTabs [aria-selected="true"] { background: #eef5fd; }
[data-testid="stPlotlyChart"], [data-testid="stDataFrame"] { background: #fff; border: 1px solid #e6e5df;
        border-radius: 16px; padding: 8px; box-shadow: 0 1px 2px rgba(0,0,0,.03); }
[data-testid="stExpander"] details { border-radius: 14px; border-color: #e6e5df; background: #fff; }
[data-testid="stMetric"] { background: #fff; border: 1px solid #e6e5df; border-radius: 16px; padding: 14px 16px; }

@media (max-width: 640px) {
  .hero { padding: 24px 20px; border-radius: 16px; }
  .hero h1 { font-size: 1.6rem; }
  .ssub { margin-left: 0; }
}
</style>
"""


def hub_color(state: str) -> str:
    return SERIES[REGION_SLOT.get(state, 0)]


def _html(s: str) -> None:
    # Strip indentation so Markdown never turns the HTML into a code block
    st.markdown("".join(line.strip() for line in s.splitlines()), unsafe_allow_html=True)


def setup_page(title: str, icon: str = "📦") -> None:
    st.set_page_config(page_title=f"{title} · Olist Supply Chain", page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, subtitle: str, chips: list[str] | None = None) -> None:
    chip_html = "".join(f'<span class="chip">{escape(c)}</span>' for c in chips or [])
    _html(f"""
    <div class="hero">
      <div class="eyebrow">{escape(eyebrow)}</div>
      <h1>{escape(title)}</h1>
      <p>{subtitle}</p>
      {f'<div class="chips">{chip_html}</div>' if chip_html else ''}
    </div>""")


def purpose(question: str, objective: str, output: str, users: str) -> None:
    """The four-card 'why does this analysis exist' strip shown at the top of every project."""
    items = [("❓", "Business question", question), ("🎯", "Objective", objective),
             ("📦", "Output", output), ("👥", "Who uses it", users)]
    cards = "".join(f'<div class="card accent"><div class="icon">{i}</div><div class="title">{t}</div>'
                    f'<div class="body">{b}</div></div>' for i, t, b in items)
    _html(f'<div class="grid c4">{cards}</div>')


def kpis(items: list[dict]) -> None:
    """items: dict(label, value, note='', tone='' | 'good' | 'bad')."""
    cards = "".join(
        f'<div class="card"><div class="label">{escape(k["label"])}</div><div class="value">{escape(str(k["value"]))}</div>'
        f'<div class="note {k.get("tone", "")}">{k.get("note", "")}</div></div>' for k in items)
    _html(f'<div class="grid c{min(len(items), 5)}">{cards}</div>')


def info_cards(items: list[tuple[str, str, str]], cols: int = 3, min_height: int = 0) -> None:
    """items: (icon, title, body). min_height keeps cards in neighbouring columns the same height."""
    style = f' style="min-height:{min_height}px"' if min_height else ""
    cards = "".join(f'<div class="card"{style}><div class="icon">{i}</div><div class="title">{t}</div>'
                    f'<div class="body">{b}</div></div>' for i, t, b in items)
    _html(f'<div class="grid c{cols}">{cards}</div>')


def callout(text: str, kind: str = "recommend") -> None:
    icon = {"recommend": "✅", "insight": "💡", "note": "ℹ️"}[kind]
    _html(f'<div class="callout {kind}"><div class="ci">{icon}</div><div>{text}</div></div>')


def section(num, title: str, subtitle: str | None = None) -> None:
    _html(f'<div class="section"><div class="num">{num}</div><div class="stitle">{escape(title)}</div></div>'
          + (f'<div class="ssub">{subtitle}</div>' if subtitle else ""))


def style_fig(fig, height: int | None = None):
    """One look for every Plotly chart: Inter, white surface, hairline grid, clean hover."""
    fig.update_layout(
        font=dict(family="Inter, system-ui, sans-serif", size=12, color="#3d3c39"),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#e1e0d9", font=dict(family="Inter", color="#0b0b0b")),
        margin=dict(l=8, r=8, t=44, b=8),
    )
    fig.update_xaxes(gridcolor="#efeee9", linecolor="#c3c2b7", zeroline=False)
    fig.update_yaxes(gridcolor="#efeee9", linecolor="#c3c2b7", zeroline=False)
    fig.update_annotations(font=dict(family="Inter", size=13, color="#0b0b0b"))
    if height:
        fig.update_layout(height=height)
    return fig


@st.cache_data
def load_site(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(SITE_OUT / f"{name}.csv", **kw)


@st.cache_data
def load_report(name: str) -> pd.DataFrame:
    return pd.read_csv(PIPE_REPORTS / f"{name}.csv")


def md_file(path: Path) -> None:
    st.markdown(path.read_text(encoding="utf-8"))


def fc_label(k: int) -> str:
    return f"{k} FC" + ("s" if k > 1 else "")
