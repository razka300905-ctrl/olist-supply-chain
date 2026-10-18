# Olist Supply Chain Portfolio

Three end-to-end supply-chain case studies on the [Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (~100k orders, 2016–2018). They are built with **Python + SQL** and presented as an interactive **Streamlit** app.

**Live app: [site-selection-vrp.streamlit.app](https://site-selection-vrp.streamlit.app/)**

| # | Project | Status | Folder |
|---|---|---|---|
| 0 | Data foundation: cleaning pipeline, cleaning log, validations | ✅ Done | [data_pipeline/](data_pipeline/README.md) |
| 1 | Site selection: how many fulfilment centres, and where? | ✅ Done | [site_selection/](site_selection/README.md) |
| 2 | Vehicle routing: delivery routes from the chosen FCs | ⏳ Next | – |
| 3 | Inventory: stock levels per FC | 🗓️ Planned | – |

## Repository layout

```
├── streamlit_app.py          # app entry point (navigation)
├── app_pages/                # one file per app page
├── app_common.py             # shared app helpers (palette, loaders)
├── requirements.txt          # app dependencies (Streamlit Cloud)
├── data_pipeline/            # raw CSV -> clean SQLite tables + cleaning log
├── site_selection/           # SQL demand model, p-median optimisation, figures, outputs
└── archive/                  # raw Kaggle CSVs (not committed, download below)
```

The app only reads the small result files in `site_selection/outputs/` and `data_pipeline/reports/`, so it runs without the raw data or the database.

## Run locally

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt -r site_selection/requirements.txt   # macOS/Linux: .venv/bin/pip
.venv/Scripts/streamlit run streamlit_app.py
```

To rebuild every result from scratch, download the dataset from Kaggle, unzip it into `archive/`, and run:

```bash
.venv/Scripts/python site_selection/run_all.py
```

## Deploy to `*.streamlit.app` (free)

1. Push this folder to a **public GitHub repository**.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and click **Create app**.
3. Pick the repository and branch, and set **Main file path** to `streamlit_app.py`.
4. Under **Advanced settings**, choose Python **3.12** or newer. Pick a custom subdomain (e.g. `olist-supply-chain`) and click **Deploy**.

---

*Data: Olist, CC BY-NC-SA 4.0. Tools: Python, SQLite, pandas, PuLP + HiGHS, Plotly, Streamlit.*
