import pandas as pd
from pathlib import Path

files = sorted(Path("data/raw").glob("no2_delhi_ncr_*.parquet"))
d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
d["date"] = pd.to_datetime(d["date"])

obs = d[d["valid"] >= 0.5]
day = d.groupby("date").agg(n=("n_granules", "first"), valid=("valid", "mean"))
day["obs_cells"] = obs.groupby("date").size()
day["obs_cells"] = day["obs_cells"].fillna(0).astype(int)
day["obs_mean"] = obs.groupby("date")["no2_umol"].mean()
holes = pd.read_csv("notes/archive_holes.csv", parse_dates=["date"])
day["short_day"] = day.index.isin(holes["date"])

# --- 1. Days with negative cell values ---
neg = d[d["no2_umol"] < 0]
neg_days = pd.DatetimeIndex(neg["date"].unique()).sort_values()
t = day.loc[neg_days, ["n", "valid", "obs_cells", "obs_mean", "short_day"]].copy()
t["negative_cells"] = neg.groupby("date").size()
print("Days with a negative cell value:")
print(t.round(2).to_string())

# --- 2. Days holding the top-100 values, against the days around them ---
top = d.nlargest(100, "no2_umol")
rows = []
for t0 in pd.DatetimeIndex(top["date"].unique()).sort_values():
    rows.append({"date": t0.date(),
                 "top100_cells": int((top["date"] == t0).sum()),
                 "obs_cells": int(day.loc[t0, "obs_cells"]),
                 "day_mean": day.loc[t0, "obs_mean"],
                 "prev_mean": day["obs_mean"].get(t0 - pd.Timedelta(days=1)),
                 "next_mean": day["obs_mean"].get(t0 + pd.Timedelta(days=1))})
print("\nDays holding the top-100 values (mean of observed cells, day before and after):")
print(pd.DataFrame(rows).round(0).to_string(index=False))

# --- 3. Coarse independent check against the ITO station (2024-25) ---
ito = Path("data/raw/ground_ito_2024-25.csv")
if ito.exists():
    g = pd.read_csv(ito)
    g["t"] = pd.to_datetime(g["Timestamp"], format="ISO8601", utc=True,
                            errors="coerce").dt.tz_localize(None)     # as-written (IST) clock
    g = g.dropna(subset=["t"])
    g = g[g["t"].dt.hour.between(12, 14)]
    gd = g.groupby(g["t"].dt.normalize())["NO2 (µg/m³)"].mean().rename("ito_no2")
    j = day[["obs_mean", "obs_cells"]].join(gd, how="inner")
    j = j[j["obs_cells"] >= 100].dropna()
    rho_all = j[["obs_mean", "ito_no2"]].corr(method="spearman").iloc[0, 1]
    jan = j[(j.index >= "2024-01-01") & (j.index < "2024-02-01")]
    rho_jan = jan[["obs_mean", "ito_no2"]].corr(method="spearman").iloc[0, 1]
    print(f"\nSatellite day mean (>=100 observed cells) vs ITO NO2 at as-written hours 12-14:")
    print(f"  all overlapping days: n={len(j)}, Spearman {rho_all:+.2f}")
    print(f"  January 2024 only:    n={len(jan)}, Spearman {rho_jan:+.2f}")
else:
    print("\nITO file not found: skipping the station check.")