"""Run the VRP project end to end (needs the clean database and project 1 outputs):
SQL delivery orders -> OR-Tools routing scenarios -> figures."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent

for step in ["01_prepare_orders.py", "02_solve_vrp.py", "03_visualize.py"]:
    print(f"\n=== vrp/{step} ===")
    runpy.run_path(str(HERE / step), run_name="__main__")
