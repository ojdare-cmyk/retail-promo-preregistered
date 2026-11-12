"""
One command runs the whole project:

    python run_all.py

1. builds the synthetic data if config.yaml says "synthetic" and the file is missing
2. splits it into training and a sealed holdout (src/prepare.py)
3. exploratory charts and a dry run on training only (src/explore_train.py)
4. opens the holdout once and runs the 5 tests (src/confirm_holdout.py);
   on any later run this step refuses and prints the stored result
5. re-runs the walkthrough notebook so its charts and tables are current
"""
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def step(script):
    print(f"\n=== {script} ===")
    subprocess.run([PY, script], cwd=ROOT / "src", check=True)


cfg = yaml.safe_load(open(ROOT / "config.yaml"))
if cfg["data"]["source"] == "synthetic" and not (ROOT / cfg["data"]["path"]).exists():
    step("generate_data.py")
step("prepare.py")
step("explore_train.py")
step("confirm_holdout.py")

nb = ROOT / "notebooks" / "walkthrough.ipynb"
if nb.exists():
    print("\n=== notebooks/walkthrough.ipynb ===")
    subprocess.run([PY, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                    "--inplace", str(nb)], check=True)
print("\nDone. Results: results/RESULTS.md and results/charts/")
