"""Pull one month of daily per-cell NO2 for a region (Phase 1).

Raw output only: no observed-cell flags here. Rules from decisions.md:
  - the single development granule PROCESSOR_VERSION 03.00.DV is excluded (D3)
  - daily value = per-pixel mean of the day's granules (D2, still open)
  - NO2 converted to umol/m2; missing stays NaN (no sentinel needed here)
"""
import time
import datetime

import ee
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import CFG, ROOT
from .grid import cells_in_bbox

NO2 = CFG["no2_band"]
BANDS = [NO2, "cloud_fraction", "solar_zenith_angle", "solar_azimuth_angle"]
NUM = ["no2_umol", "valid", "cloud", "zen", "azi"]
COLS = ["cell_id", "date", "n_granules", "algo", "proc"] + NUM
EXCLUDE_PROC = "03.00.DV"
SCALE = 1113.2


class MonthFailed(Exception):
    pass


def with_retries(fn, tries=5, base=2.0):
    """Retry with exponential backoff: waits 2, 4, 8, 16 s between attempts."""
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(base * 2 ** i)


def region_cells(region):
    b = CFG[region]
    return cells_in_bbox(b["west"], b["south"], b["east"], b["north"])


def cell_collection(cells):
    return ee.FeatureCollection([
        ee.Feature(ee.Geometry.Rectangle([r.west, r.south, r.east, r.north], None, False),
                   {"cell_id": r.cell_id})
        for r in cells.itertuples()
    ])


def pull_day(day, cells, fc):
    d0 = pd.Timestamp(day)
    d1 = d0 + pd.Timedelta(days=1)
    col = (ee.ImageCollection(CFG["no2_collection"])
           .filterDate(d0.strftime("%Y-%m-%d"), d1.strftime("%Y-%m-%d"))
           .filter(ee.Filter.neq("PROCESSOR_VERSION", EXCLUDE_PROC)))

    morning = col.filter(ee.Filter.calendarRange(5, 11, "hour"))   # Delhi passes ~06:25-08:25 UTC
    meta = with_retries(lambda: ee.Dictionary({
        "n": col.size(),
        "algo": morning.aggregate_array("ALGORITHM_VERSION").distinct(),
        "proc": morning.aggregate_array("PROCESSOR_VERSION").distinct(),
    }).getInfo())
    n = int(meta["n"])

    out = cells[["cell_id"]].copy()
    out["date"] = d0.strftime("%Y-%m-%d")
    out["n_granules"] = n
    out["algo"] = ",".join(sorted(meta["algo"]))
    out["proc"] = ",".join(sorted(meta["proc"]))
    for c in NUM:
        out[c] = np.nan
    if n == 0:                                   # no granule: 320 rows of NaN (no_overpass)
        return out[COLS]

    img = col.select(BANDS).mean()
    stack = (img.select(BANDS, ["no2", "cloud", "zen", "azi"])
             .addBands(img.select(NO2).mask().unmask(0).rename("valid")))
    res = with_retries(lambda: stack.reduceRegions(
        fc, ee.Reducer.mean(), SCALE, crs="EPSG:4326").getInfo())
    if len(res["features"]) != len(cells):
        raise RuntimeError(f"{day}: got {len(res['features'])} cells, expected {len(cells)}")

    got = (pd.DataFrame([f["properties"] for f in res["features"]])
           .reindex(columns=["cell_id", "no2", "cloud", "zen", "azi", "valid"]))
    got["no2_umol"] = got["no2"] * 1e6            # mol/m2 -> umol/m2
    got = got.drop(columns="no2")
    return out.drop(columns=NUM).merge(got, on="cell_id", how="left")[COLS]


def pull_month(region, month,verbose=True):
    cells = region_cells(region)
    fc = cell_collection(cells)
    start = pd.Timestamp(month + "-01")
    days = list(pd.date_range(start, start + pd.offsets.MonthBegin(1) - pd.Timedelta(days=1)))

    frames, failed = [], {}
    for d in days:
        try:
            f = pull_day(d, cells, fc)
            frames.append(f)
            if verbose:
                print(f"  {d.date()}  granules={f['n_granules'].iloc[0]:2d}  "
                f"cells with NO2={int(f['no2_umol'].notna().sum()):3d}", flush=True)
        except Exception as e:
                failed[d.strftime("%Y-%m-%d")] = repr(e)[:200]
                print(f"  {d.date()}  FAILED: {failed[d.strftime('%Y-%m-%d')]}", flush=True)
    if failed:
        raise MonthFailed(failed)

    df = pd.concat(frames, ignore_index=True)
    expected = len(days) * len(cells)
    if len(df) != expected or df.duplicated(["cell_id", "date"]).any():
        raise MonthFailed(f"expected {expected} unique cell-days, got {len(df)}")
    return df


def write_month(df, region, month):
    out = ROOT / "data" / "raw" / f"no2_{region}_{month}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        b"source": b"COPERNICUS/S5P/OFFL/L3_NO2 via Google Earth Engine",
        b"no2_units": b"umol/m2, tropospheric NO2 column (retrieved product, not surface NO2)",
        b"aggregation": b"per-pixel mean of the day's granules, native scale 1113.2 m, EPSG:4326",
        b"valid": b"fraction of cell area with a valid NO2 pixel (D2)",
        b"missing": b"NaN. No sentinel in this file",
        b"excluded": b"PROCESSOR_VERSION 03.00.DV (development granule)",
        b"region": region.encode(),
        b"month": month.encode(),
        b"pulled_at": datetime.datetime.now().isoformat(timespec="seconds").encode(),
    }
    table = pa.Table.from_pandas(df, preserve_index=False)
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **meta})
    tmp = out.with_suffix(".tmp")
    pq.write_table(table, tmp)
    tmp.replace(out)                              # atomic rename
    return out