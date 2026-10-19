import sys
import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init

# Usage: python scripts/04b_control_region.py 71.0 26.0 72.0 26.8
w, s, e, n = map(float, sys.argv[1:5])
init()
region = ee.Geometry.Rectangle([w, s, e, n])
band = CFG["no2_band"]


def month_feature(start_str):
    start = ee.Date(start_str)
    col = (ee.ImageCollection(CFG["no2_collection"])
           .filterDate(start, start.advance(1, "month")))
    img = col.select(band).mean()
    val = img.reduceRegion(ee.Reducer.mean(), region, 1113.2, crs="EPSG:4326").get(band)
    return ee.Feature(None, {"month": start.format("YYYY-MM"), "no2": val})


starts = [d.strftime("%Y-%m-%d")
          for d in pd.date_range("2021-07-01", "2026-09-01", freq="MS")]

rows = []
for i in range(0, len(starts), 12):
    chunk = starts[i:i + 12]
    fc = ee.FeatureCollection(ee.List(chunk).map(month_feature)).getInfo()
    rows += [f["properties"] for f in fc["features"]]
    print("batch", i // 12 + 1, "done")

df = pd.DataFrame(rows)
df["month"] = pd.to_datetime(df["month"])
df["no2"] = df["no2"] * 1e6
df = df.sort_values("month")

# Which algorithm was active mid-month (approximate; boundaries from script 03)
def algo_at(d):
    d = d + pd.Timedelta(days=14)
    if d < pd.Timestamp("2022-07-17"): return "1.5.0"
    if d < pd.Timestamp("2024-11-16"): return "1.6.0"
    if d < pd.Timestamp("2025-11-22"): return "1.7.0"
    return "1.8.0"

df["algo"] = df["month"].apply(algo_at)
df["m"] = df["month"].dt.month
df["year"] = df["month"].dt.year

# Anomaly = this month minus the average of the same calendar month across years
df["anom"] = df["no2"] - df.groupby("m")["no2"].transform("mean")

print("\nControl region monthly NO2 (umol/m2):")
print(df.pivot(index="m", columns="year", values="no2").round(1).to_string())
print("\nMean anomaly by algorithm version (a step = a version effect):")
print(df.groupby("algo")["anom"].agg(["count", "mean"]).round(2).to_string())