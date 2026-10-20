import ee
import numpy as np
import pandas as pd
from no2.config import CFG
from no2.gee import init

init()
b = CFG["delhi_ncr"]
BUFFER = 1.0          # plants just outside the box still affect it

# --- 1. Does the asset exist, and what does it hold? ---
try:
    gppd = ee.FeatureCollection("WRI/GPPD/power_plants")
    first = ee.Feature(gppd.first())
    print("Asset found. Properties:", first.propertyNames().getInfo())
    print("Total plants (world):", gppd.size().getInfo())
except Exception as e:
    raise SystemExit(f"Could not read WRI/GPPD/power_plants: {e!r}")

# --- 2. Plants within the buffered NCR box ---
region = ee.Geometry.Rectangle([b["west"] - BUFFER, b["south"] - BUFFER,
                                b["east"] + BUFFER, b["north"] + BUFFER])
sel = gppd.filterBounds(region)
feats = sel.getInfo()["features"]

rows = []
for f in feats:
    p = dict(f["properties"])
    lon, lat = f["geometry"]["coordinates"][:2]
    p["longitude"], p["latitude"] = lon, lat          # take location from the geometry
    rows.append(p)
near = pd.DataFrame(rows)
if near.empty:
    raise SystemExit("No plants found in the buffered box.")
near = near.rename(columns={"capacitymw": "capacity_mw",
                            "fuel1": "primary_fuel",
                            "comm_year": "commissioning_year"})

near["inside_box"] = (near["longitude"].between(b["west"], b["east"]) &
                      near["latitude"].between(b["south"], b["north"]))

show = [c for c in ["name", "primary_fuel", "capacity_mw", "commissioning_year",
                    "latitude", "longitude", "inside_box"] if c in near.columns]
print(f"\nPlants within {BUFFER} degree of the NCR box: {len(near)} "
      f"({int(near['inside_box'].sum())} inside the box)")
print(near[show].sort_values("capacity_mw", ascending=False).to_string(index=False))
print("\nBy fuel:", near["primary_fuel"].value_counts().to_dict())

# --- 3. Distance from every cell to the nearest plant (km, haversine) ---
cells = pd.read_parquet("data/interim/cells_static.parquet")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    a = (np.sin(np.radians(lat2 - lat1) / 2) ** 2 +
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) *
         np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


dist = np.column_stack([
    haversine_km(cells["lat"].values, cells["lon"].values, r.latitude, r.longitude)
    for r in near.itertuples()
])
cells["emit_dist_km"] = dist.min(axis=1)
print("\nDistance to nearest plant (km), over 320 cells:")
print(cells["emit_dist_km"].describe().round(1).to_string())
print("Coefficient of variation:",
      round(cells["emit_dist_km"].std() / cells["emit_dist_km"].mean(), 2))

cells.to_parquet("data/interim/cells_static.parquet", index=False)
near.to_csv("data/interim/emitters_ncr.csv", index=False)
print("\nSaved data/interim/emitters_ncr.csv and updated cells_static.parquet")