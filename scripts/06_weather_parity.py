import time
import ee
import numpy as np
import pandas as pd
from no2.config import CFG
from no2.gee import init

init()
b = CFG["delhi_ncr"]
region = ee.Geometry.Rectangle([b["west"], b["south"], b["east"], b["north"]])

ERA5 = ee.ImageCollection("ECMWF/ERA5/HOURLY")
LAND = ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")

COMMON = ["u_component_of_wind_10m", "v_component_of_wind_10m",
          "temperature_2m", "surface_pressure", "dewpoint_temperature_2m"]
SHORT = ["u", "v", "t", "sp", "td"]


def at_hour(t_str):
    t = ee.Date(t_str)
    nxt = t.advance(1, "hour")
    e5 = (ee.Image(ERA5.filterDate(t, nxt).first())
          .select(COMMON + ["boundary_layer_height"],
                  ["e5_" + s for s in SHORT] + ["e5_blh"]))
    el = (ee.Image(LAND.filterDate(t, nxt).first())
          .select(COMMON, ["el_" + s for s in SHORT]))
    d5 = e5.reduceRegion(ee.Reducer.mean(), region, 27830, crs="EPSG:4326")
    dl = el.reduceRegion(ee.Reducer.mean(), region, 11132, crs="EPSG:4326")
    return ee.Feature(None, d5.combine(dl)).set("t", t.format("YYYY-MM-dd HH:mm"))


days = pd.date_range("2024-01-01", "2024-12-31", freq="15D")
times = [f"{d.strftime('%Y-%m-%d')}T{h:02d}:00:00" for d in days for h in (7, 8)]

# --- time one single-hour request (D4: live-request speed) ---
t0 = time.perf_counter()
ee.FeatureCollection([at_hour(times[0])]).getInfo()
print(f"One single-hour request took {time.perf_counter() - t0:.1f} s\n")

# --- the sample ---
fc = ee.FeatureCollection(ee.List(times).map(at_hour)).getInfo()
df = pd.DataFrame([f["properties"] for f in fc["features"]]).dropna()
df["time"] = pd.to_datetime(df["t"])
df["hour"] = df["time"].dt.hour
df["month"] = df["time"].dt.month
df["e5_ws"] = np.hypot(df["e5_u"], df["e5_v"])
df["el_ws"] = np.hypot(df["el_u"], df["el_v"])
df.to_parquet("data/raw/weather_parity.parquet", index=False)

print("Rows:", len(df))
print("\nERA5 vs ERA5-Land over the NCR box (bias = ERA5 minus Land):")
rows = []
for name in ["u", "v", "ws", "t", "sp", "td"]:
    a, c = df[f"e5_{name}"], df[f"el_{name}"]
    rows.append({"var": name, "r": a.corr(c), "bias": (a - c).mean(),
                 "rmse": np.sqrt(((a - c) ** 2).mean()), "std_land": c.std()})
print(pd.DataFrame(rows).round(3).to_string(index=False))

print("\nBoundary layer height (m), ERA5:")
print(df.groupby("hour")["e5_blh"].describe()[["count", "mean", "min", "max"]].round(0).to_string())
print("\nBLH by month (mean of the two hours):")
print(df.groupby("month")["e5_blh"].mean().round(0).to_string())