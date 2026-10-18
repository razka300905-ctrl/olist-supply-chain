"""Shared helpers for the Streamlit portfolio app: paths, palette, cached loaders, small UI pieces."""
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
# Colour follows the hub's region so a hub keeps its colour for every k (same rule as the static maps)
REGION_SLOT = {"SP": 0, "SE": 1, "AL": 1, "BA": 1, "PE": 1, "MG": 2, "RS": 3, "GO": 4, "DF": 4, "RJ": 5}


def hub_color(state: str) -> str:
    return SERIES[REGION_SLOT.get(state, 0)]


def setup_page(title: str, icon: str = "📦") -> None:
    st.set_page_config(page_title=f"{title} · Olist Supply Chain", page_icon=icon, layout="wide")
    st.markdown(
        """<style>
        .block-container {padding-top: 2rem; max-width: 1200px;}
        [data-testid="stMetricValue"] {font-size: 1.7rem;}
        </style>""",
        unsafe_allow_html=True,
    )


@st.cache_data
def load_site(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(SITE_OUT / f"{name}.csv", **kw)


@st.cache_data
def load_report(name: str) -> pd.DataFrame:
    return pd.read_csv(PIPE_REPORTS / f"{name}.csv")


def fc_label(k: int) -> str:
    return f"{k} FC" + ("s" if k > 1 else "")
