import numpy as np
import pandas as pd
from no2.config import CFG, ROOT

RADIUS_KM = 50
BUFFER = 1.0
b = CFG["delhi_ncr"]


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2 +
         np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


plants = pd.read_csv(ROOT / "config" / "emitters_india_fossil.csv")
excl = pd.read_csv(ROOT / "config" / "emitters_exclude.csv")

for name in excl["name"]:
    n = int((plants["name"] == name).sum())
    if n != 1:
        raise SystemExit(f"Exclusion '{name}' matched {n} plants (expected 1). Check the name.")
plants = plants[~plants["name"].isin(excl["name"])].copy()
print(f"Fossil plants after exclusions: {len(plants)}")

near = plants[plants["longitude"].between(b["west"] - BUFFER, b["east"] + BUFFER) &
              plants["latitude"].between(b["south"] - BUFFER, b["north"] + BUFFER)]
print(f"\nWithin {BUFFER} degree of the NCR box: {len(near)}")
print(near[["name", "primary_fuel", "capacity_mw", "commissioning_year",
            "latitude", "longitude"]].to_string(index=False))

cells = pd.read_parquet(ROOT / "data" / "interim" / "cells_static.parquet")
D = haversine_km(cells["lat"].values[:, None], cells["lon"].values[:, None],
                 plants["latitude"].values[None, :], plants["longitude"].values[None, :])
cells["emit_dist_km"] = D.min(axis=1)
cells["emit_cap_50km_mw"] = (plants["capacity_mw"].values[None, :] * (D <= RADIUS_KM)).sum(axis=1)

for c in ("emit_dist_km", "emit_cap_50km_mw"):
    print(f"\n{c} over {len(cells)} cells:")
    print(cells[c].describe().round(1).to_string())
    print("Coefficient of variation:", round(cells[c].std() / cells[c].mean(), 2))

# --- First signal check against Jan 2024 mean NO2 (one month, correlational) ---
d = pd.read_parquet(ROOT / "data" / "interim" / "delhi_2024-01.parquet")
obs = d[d["obs_50"]].groupby("cell_id")["no2_umol"].mean().rename("no2_mean")
t = cells.merge(obs, on="cell_id")
t["dist_center_km"] = haversine_km(t["lat"].values, t["lon"].values, 28.63, 77.22)

cols = ["emit_dist_km", "emit_cap_50km_mw", "dist_center_km"]
print(f"\nSpearman correlation with mean observed NO2 (Jan 2024), {len(t)} cells:")
print(t[cols + ["no2_mean"]].corr(method="spearman")["no2_mean"].drop("no2_mean").round(2).to_string())
print("\nCorrelation among the features:")
print(t[cols].corr(method="spearman").round(2).to_string())

cells.to_parquet(ROOT / "data" / "interim" / "cells_static.parquet", index=False)
print("\nUpdated cells_static.parquet")