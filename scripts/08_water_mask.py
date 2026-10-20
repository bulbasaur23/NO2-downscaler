import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init
from no2.grid import cells_in_bbox

init()
b = CFG["delhi_ncr"]
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])

# ESA WorldCover: class 80 = permanent water bodies (10 m pixels)
land_cover = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select("Map")
water = land_cover.eq(80).rename("water")

fc = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Rectangle([r.west, r.south, r.east, r.north], None, False),
               {"cell_id": r.cell_id})
    for r in cells.itertuples()
])

out = water.reduceRegions(
    collection=fc,
    reducer=ee.Reducer.mean().setOutputs(["water_frac"]),
    scale=30,
    crs="EPSG:4326",
).getInfo()

w = pd.DataFrame([f["properties"] for f in out["features"]])
print("Columns returned:", w.columns.tolist())
df = cells.merge(w, on="cell_id")

n_missing = int(df["water_frac"].isna().sum())
print("Cells with no WorldCover value:", n_missing)
df["water_frac"] = df["water_frac"].fillna(0.0)

def classify(frac, lo, hi):
    return "water" if frac > hi else ("mixed" if frac > lo else "land")


print("Cells:", len(df))
print("\nWater fraction summary:\n", df["water_frac"].describe().round(3).to_string())

print("\nSensitivity of the land / mixed / water split to the cutoffs:")
for lo, hi in [(0.1, 0.9), (0.2, 0.8), (0.3, 0.7)]:
    print(f"  cutoffs {lo:.0%}/{hi:.0%}:",
          df["water_frac"].apply(lambda x: classify(x, lo, hi)).value_counts().to_dict())

df["water_class"] = df["water_frac"].apply(lambda x: classify(x, 0.2, 0.8))
print("\nCells with more than 5% water:")
print(df.loc[df["water_frac"] > 0.05, ["cell_id", "lon", "lat", "water_frac", "water_class"]]
      .sort_values("water_frac", ascending=False).round(3).to_string(index=False))

df.to_parquet("data/interim/cells_static.parquet", index=False)
print("\nSaved data/interim/cells_static.parquet")