import sys
import time
import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init
from no2.grid import cells_in_bbox
from no2.quota_log import log

# Usage: python scripts/09_export_cost_test.py 2024-01
month = sys.argv[1] if len(sys.argv) > 1 else "2024-01"
start = pd.Timestamp(month + "-01")
end = start + pd.offsets.MonthBegin(1)

init()
b = CFG["delhi_ncr"]
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])
cell_fc = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Rectangle([r.west, r.south, r.east, r.north], None, False),
               {"cell_id": r.cell_id})
    for r in cells.itertuples()
])

NO2 = CFG["no2_band"]
BANDS = [NO2, "cloud_fraction", "solar_zenith_angle", "solar_azimuth_angle"]
parts, skipped = [], []

for day in pd.date_range(start, end - pd.Timedelta(days=1)):
    d0 = day.strftime("%Y-%m-%d")
    d1 = (day + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    col = ee.ImageCollection(CFG["no2_collection"]).filterDate(d0, d1)
    n = col.size().getInfo()
    if n == 0:
        skipped.append(d0)
        continue

    img = col.select(BANDS).mean()
    stack = (img.select(BANDS, ["no2", "cloud", "zen", "azi"])
             .addBands(img.select(NO2).mask().unmask(0).rename("valid")))
    reduced = stack.reduceRegions(cell_fc, ee.Reducer.mean(), 1113.2, crs="EPSG:4326")

    meta = ee.Dictionary({
        "date": d0,
        "n_granules": n,
        "algo": col.aggregate_array("ALGORITHM_VERSION").distinct().join(","),
        "proc": col.aggregate_array("PROCESSOR_VERSION").distinct().join(","),
    })
    parts.append(reduced.map(lambda f: ee.Feature(f).set(meta)))


NUMERIC = ["no2", "valid", "cloud", "zen", "azi"]
SENTINEL = -9999


def fill_missing(f):
    """Every feature gets every column; a missing mean becomes the sentinel."""
    f = ee.Feature(f)
    names = f.propertyNames()
    fixed = ee.Dictionary({
        k: ee.Algorithms.If(names.contains(k), f.get(k), SENTINEL) for k in NUMERIC
    })
    base = f.toDictionary(["cell_id", "date", "n_granules", "algo", "proc"])
    return ee.Feature(None, base.combine(fixed))      # None = no geometry


table = ee.FeatureCollection(parts).flatten().map(fill_missing)


task = ee.batch.Export.table.toDrive(
    collection=table, description=f"no2_cost_test_{month}",
    folder="no2_exports", fileNamePrefix=f"cost_test_v2_{month}", fileFormat="CSV")
task.start()
print("Started task", task.id, "| days with data:", len(parts), "| skipped:", skipped)

t0 = time.perf_counter()
while True:
    s = ee.data.getTaskStatus(task.id)[0]
    elapsed = time.perf_counter() - t0
    print(f"  {elapsed:5.0f} s  {s['state']}")
    if s["state"] in ("COMPLETED", "FAILED", "CANCELLED"):
        break
    time.sleep(15)

eecu = s.get("batch_eecu_usage_seconds")
print("\nFinal state:", s["state"])
print("EECU-seconds used:", eecu if eecu is not None else "not reported: read it from the Quotas page")
if s["state"] == "FAILED":
    print("Error:", s.get("error_message"))
log(f"export {month}", round(elapsed), eecu, f"{len(parts)} days, 320 cells")