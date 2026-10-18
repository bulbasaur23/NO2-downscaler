import sys
import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init
from no2.grid import cells_in_bbox

# Usage: python scripts/00_inspect_one_day.py 2024-01-15
day = sys.argv[1] if len(sys.argv) > 1 else "2024-01-15"
next_day = (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

init()
b = CFG["delhi_ncr"]
region = ee.Geometry.Rectangle([b["west"], b["south"], b["east"], b["north"]])

col = (ee.ImageCollection(CFG["no2_collection"])
       .filterDate(day, next_day)
       .filterBounds(region))

n_images = col.size().getInfo()
print(f"Images on {day}: {n_images}")
if n_images == 0:
    sys.exit("No overpass data this day (this is the 'no_overpass' state, D6).")

# --- Inspection the plan asks for in Stage 0 ---
first = ee.Image(col.first())
print("Bands:", first.bandNames().getInfo())
print("Properties:", first.propertyNames().getInfo())   # look for processor version here (D3)
print("Native scale (m):",
      first.select(CFG["no2_band"]).projection().nominalScale().getInfo())

# --- Build per-day image: mean NO2 + valid-coverage band ---
img = col.select(CFG["no2_band"]).mean()
stack = (img.rename("no2")
         .addBands(img.mask().unmask(0).rename("valid")))

# --- One feature per grid cell ---
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])
features = [
    ee.Feature(ee.Geometry.Rectangle([r.west, r.south, r.east, r.north], None, False),
               {"cell_id": r.cell_id})
    for r in cells.itertuples()
]
fc = ee.FeatureCollection(features)

# --- Average the image inside each cell ---
out = stack.reduceRegions(
    collection=fc,
    reducer=ee.Reducer.mean(),
    scale=1113.2,
    crs="EPSG:4326",
).getInfo()

rows = [f["properties"] for f in out["features"]]
df = pd.DataFrame(rows)
df["no2"] = df["no2"] * 1e6          # mol/m2 -> umol/m2 (the unit used in the plan)
df["date"] = day
df = cells.merge(df, on="cell_id")

# --- What did we get? ---
print("\nCells total:", len(df))
print("Cells with a NO2 value:", df["no2"].notna().sum())
print("Valid fraction summary:\n", df["valid"].describe())
for thr in (0.3, 0.5, 0.7):          # D2 sensitivity check, early look
    print(f"Cells observed at >= {thr:.0%} coverage:", (df["valid"] >= thr).sum())
print("\nNO2 (umol/m2) summary:\n", df["no2"].describe())

df.to_parquet(f"data/raw/inspect_{day}.parquet", index=False)
print(f"\nSaved data/raw/inspect_{day}.parquet")