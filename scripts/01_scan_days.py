import sys
import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init

# Usage: python scripts/01_scan_days.py 2024-04-01 2024-05-01   (end date exclusive)
start = sys.argv[1] if len(sys.argv) > 1 else "2024-04-01"
end = sys.argv[2] if len(sys.argv) > 2 else "2024-05-01"

init()
b = CFG["delhi_ncr"]
region = ee.Geometry.Rectangle([b["west"], b["south"], b["east"], b["north"]])
band = CFG["no2_band"]
SCALE = 1113.2


def region_mean(img, name):
    """Mean of one band over the whole bounding box (one number)."""
    return img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=SCALE, crs="EPSG:4326"
    ).get(name)


rows = []
for day in pd.date_range(start, pd.Timestamp(end) - pd.Timedelta(days=1)):
    d0 = day.strftime("%Y-%m-%d")
    d1 = (day + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    col = (ee.ImageCollection(CFG["no2_collection"])
           .filterDate(d0, d1).filterBounds(region))
    n = col.size().getInfo()
    if n == 0:
        rows.append({"date": d0, "n_images": 0})
        print(d0, "no images")
        continue

    no2 = col.select(band).mean()
    valid = no2.mask().unmask(0).rename("valid")
    cloud = col.select("cloud_fraction").mean()

    stats = ee.Dictionary({
        "valid_frac": region_mean(valid, "valid"),
        "cloud_frac": region_mean(cloud, "cloud_fraction"),
        "no2_mean": region_mean(no2, band),
        "versions": col.aggregate_array("PROCESSOR_VERSION").distinct(),
    }).getInfo()

    rows.append({"date": d0, "n_images": n, **stats})
    print(d0, n, "valid=%.2f" % (stats["valid_frac"] or 0),
          "cloud=", stats["cloud_frac"], stats["versions"])

df = pd.DataFrame(rows)
df.to_parquet(f"data/raw/scan_{start}_{end}.parquet", index=False)
print("\nDays with >=50% valid area:", (df["valid_frac"] >= 0.5).sum(), "of", len(df))