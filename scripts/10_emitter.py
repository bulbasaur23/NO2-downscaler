import numpy as np
import pandas as pd
from no2.config import CFG

b = CFG["delhi_ncr"]
BUFFER = 1.0          # plants just outside the box still affect it

p = pd.read_csv("data/raw/global_power_plant_database.csv", low_memory=False)
print("Columns:", p.columns.tolist())
print("Rows (world):", len(p))

p = p[p["country"] == "IND"]
near = p[(p["longitude"].between(b["west"] - BUFFER, b["east"] + BUFFER)) &
         (p["latitude"].between(b["south"] - BUFFER, b["north"] + BUFFER))].copy()
near["inside_box"] = (near["longitude"].between(b["west"], b["east"]) &
                      near["latitude"].between(b["south"], b["north"]))

cols = [c for c in ["name", "primary_fuel", "capacity_mw", "commissioning_year",
                    "latitude", "longitude", "inside_box"] if c in near.columns]
print(f"\nPlants within {BUFFER} degree of the NCR box: {len(near)} "
      f"({int(near['inside_box'].sum())} inside the box)")
print(near[cols].sort_values("capacity_mw", ascending=False).to_string(index=False))
print("\nBy fuel:", near["primary_fuel"].value_counts().to_dict())

# --- distance from every cell to the nearest plant (km, haversine) ---
cells = pd.read_parquet("data/interim/cells_static.parquet")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    a = (np.sin(np.radians(lat2 - lat1) / 2) ** 2 +
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) *
         np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


dist = np.column_stack([
    haversine_km(cells["lat"].values, cells["lon"].values, row.latitude, row.longitude)
    for row in near.itertuples()
])
cells["emit_dist_km"] = dist.min(axis=1)
print("\nDistance to nearest plant (km), over 320 cells:")
print(cells["emit_dist_km"].describe().round(1).to_string())
print("Coefficient of variation:", round(cells["emit_dist_km"].std() / cells["emit_dist_km"].mean(), 2))

cells.to_parquet("data/interim/cells_static.parquet", index=False)
near.to_csv("data/interim/emitters_ncr.csv", index=False)
print("\nSaved data/interim/emitters_ncr.csv and updated cells_static.parquet")