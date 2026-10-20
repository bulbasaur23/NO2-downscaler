import math
import sys
import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init
from no2.solar import observation_utc_hours, hhmm

# Usage: python scripts/07b_overpass_times_month.py 2024-01-01
start = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2024-01-01")
end = start + pd.offsets.MonthBegin(1)

init()
b = CFG["delhi_ncr"]
region = ee.Geometry.Rectangle([b["west"], b["south"], b["east"], b["north"]])
LON, LAT = (b["west"] + b["east"]) / 2, (b["south"] + b["north"]) / 2
NO2 = CFG["no2_band"]


def per_granule(img):
    img = ee.Image(img)
    azi_rad = img.select("solar_azimuth_angle").multiply(math.pi / 180)
    stack = ee.Image.cat([
        img.select("solar_zenith_angle").rename("zen"),
        azi_rad.sin().rename("azi_sin"),
        azi_rad.cos().rename("azi_cos"),
        img.select("solar_zenith_angle").mask().unmask(0).rename("ang_valid"),
        img.select(NO2).mask().unmask(0).rename("no2_valid"),
    ])
    stats = stack.reduceRegion(ee.Reducer.mean(), region, 1113.2, crs="EPSG:4326")
    return ee.Feature(None, stats).set("t", img.get("system:time_start"))


# Delhi is only ever crossed in the morning-to-midday UTC window, so skip the rest
col = (ee.ImageCollection(CFG["no2_collection"])
       .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
       .filter(ee.Filter.calendarRange(5, 11, "hour")))

feats = col.map(per_granule).getInfo()["features"]
df = pd.DataFrame([f["properties"] for f in feats])
df["time"] = pd.to_datetime(df["t"], unit="ms")
df["date"] = df["time"].dt.date
df = df[df["ang_valid"] > 0.05].copy()                 # granules that cover the box

df["azi"] = [math.degrees(math.atan2(s, c)) for s, c in zip(df["azi_sin"], df["azi_cos"])]
df["utc_h"] = [observation_utc_hours(t.dayofyear, z, a, LON, LAT)
               for t, z, a in zip(df["time"], df["zen"], df["azi"])]
df["utc"] = df["utc_h"].apply(hhmm)
df["granule_start"] = df["time"].dt.strftime("%H:%M")
df["diff_min"] = (df["utc_h"] - (df["time"].dt.hour + df["time"].dt.minute / 60)) * 60

print(df[["date", "granule_start", "utc", "diff_min", "ang_valid", "no2_valid"]]
      .round(2).to_string(index=False))

per_day = df.groupby("date").size()
print("\nGranules covering the box per day: ", per_day.value_counts().to_dict())
print("Observation time (UTC): earliest", hhmm(df["utc_h"].min()),
      " latest", hhmm(df["utc_h"].max()),
      " spread (min):", round((df["utc_h"].max() - df["utc_h"].min()) * 60))
print("Granule start vs observation time (min): mean",
      round(df["diff_min"].mean(), 1), " std", round(df["diff_min"].std(), 1))
print("Days with solar angles but almost no NO2 (no2_valid < 0.1):",
      int(((df["ang_valid"] > 0.5) & (df["no2_valid"] < 0.1)).sum()))