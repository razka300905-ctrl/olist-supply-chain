"""Olist supply-chain portfolio - Streamlit entry point.

Run locally:  streamlit run streamlit_app.py
Each page lives in app_pages/; add VRP and inventory pages to the list below as they are built.
"""
import streamlit as st

pages = {
    "Portfolio": [st.Page("app_pages/home.py", title="Home", icon="🏠", default=True)],
    "Projects": [
        st.Page("app_pages/data_cleaning.py", title="0 · Data cleaning", icon="🧹"),
        st.Page("app_pages/site_selection.py", title="1 · Site selection", icon="📍"),
        st.Page("app_pages/vrp.py", title="2 · Vehicle routing", icon="🚚"),
        st.Page("app_pages/inventory.py", title="3 · Inventory", icon="📦"),
    ],
}
st.navigation(pages).run()
