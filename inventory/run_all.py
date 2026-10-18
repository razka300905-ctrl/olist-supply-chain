"""Run the inventory project end to end (needs the clean database and project 1 outputs):
SQL demand -> segmentation -> forecast backtests (product + daily) -> policy simulation -> figures."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent

for step in ["01_prepare_demand.py", "02_segment.py", "03_forecast.py", "03b_forecast_daily.py", "04_policy_simulation.py", "05_visualize.py"]:
    print(f"\n=== inventory/{step} ===")
    runpy.run_path(str(HERE / step), run_name="__main__")
