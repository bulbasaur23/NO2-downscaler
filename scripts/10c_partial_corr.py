import numpy as np
import pandas as pd
from no2.config import ROOT

cells = pd.read_parquet(ROOT / "data" / "interim" / "cells_static.parquet")
d = pd.read_parquet(ROOT / "data" / "interim" / "delhi_2024-01.parquet")

obs = (d[d["obs_50"]].groupby("cell_id")["no2_umol"].agg(["mean", "count"])
       .rename(columns={"mean": "no2_mean", "count": "n_obs"}))
t = cells.merge(obs, on="cell_id")
print("Observed days per cell: min", int(t["n_obs"].min()),
      " median", int(t["n_obs"].median()), " max", int(t["n_obs"].max()))


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2 +
         np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


t["dist_center_km"] = haversine_km(t["lat"].values, t["lon"].values, 28.63, 77.22)
r = t[["no2_mean", "emit_dist_km", "emit_cap_50km_mw", "dist_center_km"]].rank()


def resid(y, x):
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def partial(a, b, control):
    ra = resid(r[a].values, r[control].values)
    rb = resid(r[b].values, r[control].values)
    return np.corrcoef(ra, rb)[0, 1]


print("\nSpearman-style partial correlation with mean NO2, controlling for distance to centre:")
for f in ("emit_dist_km", "emit_cap_50km_mw"):
    print(f"  {f:18s} raw {r[['no2_mean', f]].corr().iloc[0, 1]:+.2f}"
          f"   partial {partial('no2_mean', f, 'dist_center_km'):+.2f}")
print("\nFor comparison, distance to centre controlling for emit_dist_km:")
print(f"  dist_center_km     raw {r[['no2_mean', 'dist_center_km']].corr().iloc[0, 1]:+.2f}"
      f"   partial {partial('no2_mean', 'dist_center_km', 'emit_dist_km'):+.2f}")