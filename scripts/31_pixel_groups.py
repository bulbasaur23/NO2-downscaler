import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init
from no2.grid import cells_in_bbox
from no2.weather_pull import ERA5, VARS, SHORT, SCALE, GROUPS

init()
b = CFG["delhi_ncr"]
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])
pts = ee.FeatureCollection([
    ee.Feature(ee.Geometry.Point([r.lon, r.lat]), {"cell_id": r.cell_id})
    for r in cells.itertuples()])

frames = []
for i, t0 in enumerate(["2024-01-15T08:00:00", "2024-07-15T08:00:00"]):
    t = ee.Date(t0)
    img = (ee.Image(ee.ImageCollection(ERA5).filterDate(t, t.advance(1, "hour")).first())
           .select(VARS[:5], SHORT[:5]))
    res = img.reduceRegions(pts, ee.Reducer.first(), SCALE, crs="EPSG:4326").getInfo()
    f = pd.DataFrame([x["properties"] for x in res["features"]]).set_index("cell_id")
    frames.append(f.add_suffix(f"_{i}"))
sig = pd.concat(frames, axis=1)

key = sig.round(5).apply(lambda r: tuple(r.values), axis=1)
codes, _ = pd.factorize(key)
g = cells.set_index("cell_id").join(pd.Series(codes, index=sig.index, name="rep"))

rows, info = [], []
for rep, grp in g.groupby("rep"):
    cx, cy = grp["lon"].mean(), grp["lat"].mean()
    rc = ((grp["lon"] - cx) ** 2 + (grp["lat"] - cy) ** 2).idxmin()      # most central cell
    rows.append({"rep": rep, "rep_cell": rc, "rep_lon": grp.loc[rc, "lon"],
                 "rep_lat": grp.loc[rc, "lat"],
                 "sig_u10": sig.loc[rc, "u10_0"], "sig_v10": sig.loc[rc, "v10_0"],
                 "sig_t2m": sig.loc[rc, "t2m_0"]})
    info.append({"rep": rep, "n_cells": len(grp),
                 "lon": f"{grp['lon'].min():.3f}-{grp['lon'].max():.3f}",
                 "lat": f"{grp['lat'].min():.3f}-{grp['lat'].max():.3f}",
                 "full_rectangle": len(grp) == grp["lon"].nunique() * grp["lat"].nunique()})

print("ERA5 pixel groups found:", len(rows))
print(pd.DataFrame(info).to_string(index=False))
print("All groups are full rectangles:", all(i["full_rectangle"] for i in info))

out = g.reset_index()[["cell_id", "rep"]].merge(pd.DataFrame(rows), on="rep")
GROUPS.parent.mkdir(parents=True, exist_ok=True)
out.to_parquet(GROUPS, index=False)
print("Saved", GROUPS, "|", len(out), "cells")