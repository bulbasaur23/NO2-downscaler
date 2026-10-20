import numpy as np
import pandas as pd
from no2.config import ROOT

cells = pd.read_parquet(ROOT / "data" / "interim" / "cells_static.parquet")
d = pd.read_parquet(ROOT / "data" / "interim" / "delhi_2024-01.parquet")
obs = d[d["obs_50"]].groupby("cell_id")["no2_umol"].mean().rename("no2_mean")
t = cells.merge(obs, on="cell_id")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2 +
         np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


t["dist_center_km"] = haversine_km(t["lat"].values, t["lon"].values, 28.63, 77.22)
ranks = t[["no2_mean", "emit_dist_km", "emit_cap_50km_mw"]].rank()

la = (t["lat"] - t["lat"].mean()) / t["lat"].std()
lo = (t["lon"] - t["lon"].mean()) / t["lon"].std()
controls = {
    "distance to centre": np.column_stack([t["dist_center_km"]]),
    "lat + lon (plane)": np.column_stack([la, lo]),
    "quadratic spatial surface": np.column_stack([la, lo, la**2, lo**2, la * lo]),
    "surface + distance to centre": np.column_stack([la, lo, la**2, lo**2, la * lo, t["dist_center_km"]]),
}


def resid(y, X):
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


print(f"Rank-based partial correlation with mean observed NO2 ({len(t)} cells):")
print(f"{'controlling for':32s} {'emit_dist_km':>13s} {'emit_cap_50km_mw':>17s}")
for name, X in controls.items():
    y = resid(ranks["no2_mean"].values, X)
    out = []
    for f in ("emit_dist_km", "emit_cap_50km_mw"):
        out.append(np.corrcoef(y, resid(ranks[f].values, X))[0, 1])
    print(f"{name:32s} {out[0]:+13.2f} {out[1]:+17.2f}")