import ee
import pandas as pd
from no2.config import CFG, ROOT
from no2.gee import init
from no2.grid import cells_in_bbox

init()
b = CFG["delhi_ncr"]
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])
fc = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Rectangle([r.west, r.south, r.east, r.north], None, False),
               {"cell_id": r.cell_id})
    for r in cells.itertuples()])

srtm = ee.Image("USGS/SRTMGL1_003").select("elevation")
elev_1km = (srtm.reduceResolution(reducer=ee.Reducer.mean(), maxPixels=4096)
            .reproject(crs="EPSG:4326", scale=1113.2))
red = (ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True)
       .combine(ee.Reducer.max(), sharedInputs=True))


def per_cell(img, scale, prefix, tile=1):
    res = img.reduceRegions(collection=fc, reducer=red, scale=scale,
                            crs="EPSG:4326", tileScale=tile).getInfo()
    df = pd.DataFrame([f["properties"] for f in res["features"]])
    return df.rename(columns={"mean": f"{prefix}_mean", "stdDev": f"{prefix}_std",
                              "max": f"{prefix}_max"})


e1 = per_cell(elev_1km, 1113.2, "elev")
e30 = per_cell(srtm, 30, "e30", tile=4)
e = cells[["cell_id"]].merge(e1, on="cell_id", how="left").merge(e30, on="cell_id", how="left")

print("Cells:", len(e), "| missing elev_mean:", int(e["elev_mean"].isna().sum()),
      "| missing e30_mean:", int(e["e30_mean"].isna().sum()))
print("\nElevation per cell (m), 1 km version:")
print(e[["elev_mean", "elev_std", "elev_max"]].describe().loc[["min", "25%", "50%", "75%", "max"]].round(1).to_string())
print("\n1 km vs 30 m (per cell):")
print("  max |mean difference| (m):", round(float((e["elev_mean"] - e["e30_mean"]).abs().max()), 2))
print("  std at 30 m / std at 1 km: median", round(float((e["e30_std"] / e["elev_std"]).median()), 2),
      " p95", round(float((e["e30_std"] / e["elev_std"]).quantile(0.95)), 2))
print("  cells with 1 km std > 10 m:", int((e["elev_std"] > 10).sum()),
      "| with 30 m std > 10 m:", int((e["e30_std"] > 10).sum()))
hi = e.merge(cells[["cell_id", "lon", "lat"]], on="cell_id").nlargest(5, "elev_mean")
print("\nHighest five cells:")
print(hi[["cell_id", "lon", "lat", "elev_mean", "elev_std", "elev_max"]].round(1).to_string(index=False))

path = ROOT / "data" / "interim" / "cells_static.parquet"
st = pd.read_parquet(path).drop(columns=["elev_mean", "elev_std", "elev_max"], errors="ignore")
st.merge(e[["cell_id", "elev_mean", "elev_std", "elev_max"]], on="cell_id", how="left").to_parquet(path, index=False)
print("\nUpdated", path)