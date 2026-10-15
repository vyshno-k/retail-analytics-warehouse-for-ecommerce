"""One command: dbt deps -> seed -> build -> dashboard opens in your browser.
Usage:  python run_all.py
"""
import shutil, subprocess, sys

dbt = shutil.which("dbt")
if not dbt:
    sys.exit("dbt not found. Activate your virtual environment first (see SETUP.md).")
for cmd in (["deps"], ["seed"], ["build"]):
    print(f"\n=== dbt {' '.join(cmd)} ===")
    if subprocess.call([dbt, *cmd]) != 0:
        sys.exit(f"dbt {' '.join(cmd)} failed. Fix the error above, then re-run.")
print("\n=== building dashboard ===")
sys.exit(subprocess.call([sys.executable, "dashboard/build_dashboard.py"]))
