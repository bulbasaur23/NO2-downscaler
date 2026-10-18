import sys
import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init

# Usage: python scripts/02_inspect_images.py 2024-01-28
day = sys.argv[1] if len(sys.argv) > 1 else "2024-01-28"
next_day = (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

init()
b = CFG["delhi_ncr"]
region = ee.Geometry.Rectangle([b["west"], b["south"], b["east"], b["north"]])
band = CFG["no2_band"]


def describe(img):
    img = ee.Image(img)
    no2_mask = img.select(band).mask().unmask(0)
    cloud_mask = img.select("cloud_fraction").mask().unmask(0)
    red = ee.Reducer.mean()
    return ee.Feature(None, {
        "orbit": img.get("ORBIT"),
        "time": img.get("system:time_start"),
        "status": img.get("PROCESSING_STATUS"),
        "quality": img.get("PRODUCT_QUALITY"),
        "no2_valid": no2_mask.reduceRegion(red, region, 1113.2, crs="EPSG:4326").get(band),
        "cloud_valid": cloud_mask.reduceRegion(red, region, 1113.2, crs="EPSG:4326").get("cloud_fraction"),
    })


col = (ee.ImageCollection(CFG["no2_collection"])
       .filterDate(day, next_day).filterBounds(region))
res = col.map(describe).getInfo()
df = pd.DataFrame([f["properties"] for f in res["features"]])
df["time"] = pd.to_datetime(df["time"], unit="ms")
print(df.sort_values("time").to_string())