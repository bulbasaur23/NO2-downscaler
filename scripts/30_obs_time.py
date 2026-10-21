import pandas as pd
from pathlib import Path
from no2.config import CFG, ROOT
from no2.grid import cells_in_bbox
from no2.solar import observation_utc_hours, hhmm

b = CFG["delhi_ncr"]
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])[["cell_id", "lon", "lat"]]

files = sorted(Path("data/raw").glob("no2_delhi_ncr_*.parquet"))
d = pd.concat([pd.read_parquet(f, columns=["cell_id", "date", "zen", "azi"]) for f in files],
              ignore_index=True)
d["date"] = pd.to_datetime(d["date"])
all_dates = pd.DatetimeIndex(sorted(d["date"].unique()))

a = d.dropna(subset=["zen", "azi"]).merge(cells, on="cell_id")
a["doy"] = a["date"].dt.dayofyear
a["t"] = [observation_utc_hours(n, z, az, lo, la)
          for n, z, az, lo, la in zip(a["doy"], a["zen"], a["azi"], a["lon"], a["lat"])]

g = a.groupby("date")["t"]
day = pd.DataFrame({
    "n_cells": g.size(),
    "obs_utc_hour": g.median(),
    "spread_min": (g.quantile(0.9) - g.quantile(0.1)) * 60,
    "range_min": (g.max() - g.min()) * 60,
}).reindex(all_dates)
day["n_cells"] = day["n_cells"].fillna(0).astype(int)
day["flag"] = day["spread_min"] > 15

has = day["obs_utc_hour"].notna()
print(f"Days: {len(day)}   with an observation time: {int(has.sum())}   "
      f"without (no angles): {int((~has).sum())}")
print("Observation time (UTC): earliest", hhmm(day["obs_utc_hour"].min()),
      " latest", hhmm(day["obs_utc_hour"].max()))
print("Cells with angles per day: median", int(day.loc[has, "n_cells"].median()),
      " min", int(day.loc[has, "n_cells"].min()))

s = day.loc[has, "spread_min"]
print("\nWithin-day spread of per-cell times (p90 - p10, minutes): median",
      round(s.median(), 1), " p95", round(s.quantile(0.95), 1), " max", round(s.max(), 1))
fl = day[day["flag"]]
print(f"Days with spread > 15 min: {len(fl)} ({len(fl) / has.sum():.1%})")
if len(fl):
    print(fl[["n_cells", "spread_min", "range_min"]].round(1).head(15).to_string())

ref = {"2024-01-02": "08:31", "2024-01-15": "07:46", "2024-01-29": "08:22",
       "2024-07-01": "08:36", "2024-07-15": "07:34"}
print("\nCross-check against scripts/07b (computed from granule-level angles):")
for dt, r in ref.items():
    v = day.loc[pd.Timestamp(dt), "obs_utc_hour"]
    print(f"  {dt}: 07b {r}   this {hhmm(v) if pd.notna(v) else 'n/a'}")

t = day["obs_utc_hour"]
step = (t.diff() * 60).dropna()
drift = int(step.between(-25, -13).sum())
jump = int((step > 60).sum())
print(f"\nDay-to-day change in observation time ({len(step)} consecutive-day pairs):")
print(f"  steady drift (-25 to -13 min): {drift}   jump (> +60 min): {jump}   "
      f"other: {len(step) - drift - jump}")

out = ROOT / "data" / "interim" / "obs_time_delhi.parquet"
day.reset_index(names="date").to_parquet(out, index=False)
print("\nSaved", out)