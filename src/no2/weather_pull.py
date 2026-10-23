"""Hourly ERA5 at one representative point per ERA5 pixel (Phase 1.3b).

Cells are mapped to pixels empirically (scripts/31): cells whose sampled ERA5 values are
identical sit in the same pixel. A cell's weather is the pixel containing its centre
(nearest pixel, no spatial interpolation).
"""
import datetime

import ee
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import ROOT
from .pull import with_retries

ERA5 = "ECMWF/ERA5/HOURLY"
VARS = ["u_component_of_wind_10m", "v_component_of_wind_10m", "temperature_2m",
        "dewpoint_temperature_2m", "surface_pressure", "total_precipitation",
        "boundary_layer_height"]
SHORT = ["u10", "v10", "t2m", "d2m", "sp", "tp", "blh"]
SCALE = 27830
GROUPS = ROOT / "data" / "interim" / "era5_pixel_groups.parquet"


def load_reps():
    g = pd.read_parquet(GROUPS)
    return g.drop_duplicates("rep")[["rep", "rep_lon", "rep_lat"]].sort_values("rep")


def reps_collection(reps):
    return ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point([r.rep_lon, r.rep_lat]), {"rep": int(r.rep)})
        for r in reps.itertuples()])


def pull_chunk(reps_fc, a, b):
    col = ee.ImageCollection(ERA5).filterDate(a, b).select(VARS, SHORT)

    def per_image(img):
        img = ee.Image(img)
        t = img.get("system:time_start")
        fc = img.reduceRegions(reps_fc, ee.Reducer.first(), SCALE, crs="EPSG:4326")
        return fc.map(lambda f: ee.Feature(f).set("t", t))

    fc = col.map(per_image).flatten().select(["rep", "t"] + SHORT, retainGeometry=False)
    res = with_retries(lambda: fc.getInfo())
    return pd.DataFrame([f["properties"] for f in res["features"]])


def pull_month(month):
    reps = load_reps()
    reps_fc = reps_collection(reps)
    start = pd.Timestamp(month + "-01")
    end = start + pd.offsets.MonthBegin(1)
    edges = list(pd.date_range(start, end, freq="7D"))
    if edges[-1] != end:
        edges.append(end)
    frames = [pull_chunk(reps_fc, a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d"))
              for a, b in zip(edges[:-1], edges[1:])]
    df = pd.concat(frames, ignore_index=True).reindex(columns=["rep", "t"] + SHORT)
    df["time"] = pd.to_datetime(df["t"], unit="ms")                 # UTC, naive
    df["rep"] = df["rep"].astype(int)
    df = df.drop(columns="t").sort_values(["time", "rep"]).reset_index(drop=True)
    expected = int((end - start) / pd.Timedelta(hours=1)) * len(reps)
    if len(df) != expected or df.duplicated(["time", "rep"]).any():
        raise RuntimeError(f"{month}: expected {expected} unique rows, got {len(df)}")
    return df[["time", "rep"] + SHORT]


def write_month(df, month):
    out = ROOT / "data" / "raw" / f"era5_delhi_ncr_{month}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        b"source": b"ECMWF/ERA5/HOURLY via Google Earth Engine",
        b"units": b"u10,v10 m/s; t2m,d2m K; sp Pa; tp m (accumulation, convention unverified); blh m",
        b"time": b"UTC, hourly timestamps as given by system:time_start",
        b"rep": b"ERA5 pixel group id; cell mapping in data/interim/era5_pixel_groups.parquet",
        b"month": month.encode(),
        b"pulled_at": datetime.datetime.now().isoformat(timespec="seconds").encode(),
    }
    table = pa.Table.from_pandas(df, preserve_index=False)
    table = table.replace_schema_metadata({**(table.schema.metadata or {}), **meta})
    tmp = out.with_suffix(".tmp")
    pq.write_table(table, tmp)
    tmp.replace(out)
    return out