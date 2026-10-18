"""Run the full site-selection pipeline:
raw CSV -> SQLite raw layer -> clean layer -> SQL demand model -> optimisation -> figures."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
PIPELINE = HERE.parent / "data_pipeline"

STEPS = [
    PIPELINE / "01_load_raw.py",
    PIPELINE / "02_clean.py",
    HERE / "01_run_sql.py",
    HERE / "02_optimize_sites.py",
    HERE / "03_visualize.py",
]

for step in STEPS:
    print(f"\n=== {step.parent.name}/{step.name} ===")
    runpy.run_path(str(step), run_name="__main__")
