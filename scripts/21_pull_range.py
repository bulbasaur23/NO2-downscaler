import re
import sys
import time
import pandas as pd
from no2.gee import init
from no2.runner import run_month

# Usage: python scripts/21_pull_range.py 2022-07 2026-09
REGION = "delhi_ncr"
start, end = sys.argv[1], sys.argv[2]
for m in (start, end):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", m):
        sys.exit(f"Months must look like 2024-01, got {m!r}")

months = [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]
init()
t0 = time.perf_counter()
results = {}
for i, m in enumerate(months, 1):
    r = run_month(REGION, m)
    results[m] = r
    extra = r.get("status_counts") or r.get("error", "")
    print(f"[{i:2d}/{len(months)}] {m}  {r['state']:7s} {str(r.get('sec', '')):>4}s  {extra}", flush=True)

states = pd.Series({m: r["state"] for m, r in results.items()}).value_counts().to_dict()
print("\nSummary:", states, f"| total {round((time.perf_counter() - t0) / 60, 1)} min")
failed = [m for m, r in results.items() if r["state"] == "failed"]
if failed:
    print("Failed months (rerun the same command to retry only these):", failed)