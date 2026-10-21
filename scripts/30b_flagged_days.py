import numpy as np
import pandas as pd
from pathlib import Path
from no2.config import CFG, ROOT
from no2.grid import cells_in_bbox
from no2.solar import observation_utc_hours, hhmm

b = CFG["delhi_ncr"]
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])[["cell_id", "lon", "lat"]]
day = pd.read_parquet(ROOT / "data" / "interim" / "obs_time_delhi.parquet")
day["date"] = pd.to_datetime(day["date"])
day = day.set_index("date")
has = day["obs_utc_hour"].notna()
fset = set(day.index[day["flag"]])

# --- 1. Are the flagged days the two-granule days found by scripts/07b? ---
two = {"2024-01": ["2024-01-06", "2024-01-17", "2024-01-22"],
       "2024-07": ["2024-07-11", "2024-07-16", "2024-07-27"]}
print("Flagged days vs the two-granule days found by 07b:")
for m, ds in two.items():
    fl = day.index[(day.index.strftime("%Y-%m") == m) & day["flag"]].strftime("%Y-%m-%d").tolist()
    print(f"  {m}: flagged   {fl}")
    print(f"       07b found {ds}")

# --- 2. Share of flagged days by calendar month ---
share = day[has].groupby(day[has].index.month)["flag"].mean()
print("\nShare of days flagged, by calendar month:")
print(share.round(2).to_string())

# --- 3. The earliest and latest times: flagged days or not? ---
t = day.loc[has, "obs_utc_hour"]
for label, s in (("earliest", t.nsmallest(5)), ("latest", t.nlargest(5))):
    print(f"\n{label} five (date, time, flagged):",
          [(i.strftime("%Y-%m-%d"), hhmm(v), bool(day.loc[i, 'flag'])) for i, v in s.items()])

# --- 4. Per-cell structure: all flagged days plus 150 random normal days ---
files = sorted(Path("data/raw").glob("no2_delhi_ncr_*.parquet"))
d = pd.concat([pd.read_parquet(f, columns=["cell_id", "date", "zen", "azi"]) for f in files],
              ignore_index=True)
d["date"] = pd.to_datetime(d["date"])
normal = day.index[has & ~day["flag"]]
sample = normal[np.random.default_rng(0).choice(len(normal), size=150, replace=False)]
keep = day.index[day["flag"]].union(sample)
d = d[d["date"].isin(keep)].dropna(subset=["zen", "azi"]).merge(cells, on="cell_id")
d["t"] = [observation_utc_hours(x.dayofyear, z, a, lo, la)
          for x, z, a, lo, la in zip(d["date"], d["zen"], d["azi"], d["lon"], d["lat"])]

rows = []
for dt, g in d.groupby("date"):
    med = g["t"].median()
    rows.append({"flag": dt in fset,
                 "rho_lon": g["t"].rank().corr(g["lon"].rank()),
                 "off10": float(((g["t"] - med).abs() > 10 / 60).mean())})
r = pd.DataFrame(rows)
r["abs_rho"] = r["rho_lon"].abs()
print("\nPer-cell structure:")
print(r.groupby("flag").agg(days=("rho_lon", "size"),
                            rho_median=("rho_lon", "median"),
                            abs_rho_median=("abs_rho", "median"),
                            cells_off_10min_median=("off10", "median"),
                            cells_off_10min_p95=("off10", lambda s: s.quantile(0.95))).round(2).to_string())