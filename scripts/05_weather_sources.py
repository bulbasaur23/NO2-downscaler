import ee
import pandas as pd
from no2.gee import init

init()

CANDIDATES = {
    "ERA5-Land hourly": "ECMWF/ERA5_LAND/HOURLY",
    "ERA5-Land daily aggregates": "ECMWF/ERA5_LAND/DAILY_AGGR",
    "ERA5 hourly (single levels)": "ECMWF/ERA5/HOURLY",
    "ERA5 daily": "ECMWF/ERA5/DAILY",
}
today = pd.Timestamp.now().normalize()
window_end = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

for name, cid in CANDIDATES.items():
    print("=" * 70)
    print(name, "->", cid)
    try:
        col = ee.ImageCollection(cid)
        first = ee.Image(col.first())
        bands = first.bandNames().getInfo()
        scale = first.select(0).projection().nominalScale().getInfo()

        recent = col.filterDate("2025-06-01", window_end)
        last_ms = recent.aggregate_max("system:time_start").getInfo()
        last = pd.to_datetime(last_ms, unit="ms") if last_ms else None

        print("Native scale (m):", round(scale))
        print("Number of bands:", len(bands))
        print("Bands:", bands)
        print("Latest image:", last)
        if last is not None:
            print("Lag behind today (days):", (today - last.normalize()).days)

        blh = [x for x in bands if "boundary" in x.lower() or "blh" in x.lower()]
        print("Boundary-layer-height bands:", blh if blh else "NONE FOUND")
    except Exception as e:
        print("Could not read this collection:", repr(e))