import datetime
import re
import sys
import time
import pandas as pd
from no2 import manifest
from no2.gee import init
from no2.weather_pull import pull_month, write_month

# Usage: python scripts/32_pull_era5.py 2022-06 2026-09
REGION = "era5_delhi_ncr"
start, end = sys.argv[1], sys.argv[2]
for m in (start, end):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", m):
        sys.exit(f"Months must look like 2024-01, got {m!r}")
months = [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]

init()
t_all = time.perf_counter()
states = {}
for i, m in enumerate(months, 1):
    row = manifest.get(REGION, m)
    if row and row["status"] == "done":
        states[m] = "skipped"
        print(f"[{i:2d}/{len(months)}] {m}  skipped", flush=True)
        continue
    attempts = (int(row["attempts"]) + 1) if row and row["attempts"] else 1
    manifest.update(REGION, m, status="running", attempts=attempts, error="")
    t0 = time.perf_counter()
    try:
        df = pull_month(m)
        write_month(df, m)
    except Exception as e:
        manifest.update(REGION, m, status="failed", error=repr(e)[:300])
        states[m] = "failed"
        print(f"[{i:2d}/{len(months)}] {m}  FAILED  {repr(e)[:150]}", flush=True)
        continue
    sec = round(time.perf_counter() - t0)
    manifest.update(REGION, m, status="done", rows=len(df), wall_seconds=sec, error="",
                    days=df["time"].dt.normalize().nunique(),
                    finished_at=datetime.datetime.now().isoformat(timespec="seconds"))
    states[m] = "done"
    print(f"[{i:2d}/{len(months)}] {m}  done  {sec:3d}s  rows={len(df)}", flush=True)

print("\nSummary:", pd.Series(states).value_counts().to_dict(),
      f"| total {round((time.perf_counter() - t_all) / 60, 1)} min")