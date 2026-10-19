import math
import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init

init()
LON, LAT = 77.2, 28.6                      # central Delhi
spot = ee.Geometry.Point([LON, LAT]).buffer(5000)


def overpass_utc(day):
    d0 = pd.Timestamp(day)
    d1 = d0 + pd.Timedelta(days=1)
    col = (ee.ImageCollection(CFG["no2_collection"])
           .filterDate(d0.strftime("%Y-%m-%d"), d1.strftime("%Y-%m-%d"))
           .select(["solar_zenith_angle", "solar_azimuth_angle"]))
    vals = col.mean().reduceRegion(ee.Reducer.mean(), spot, 1113.2).getInfo()
    z, az = vals.get("solar_zenith_angle"), vals.get("solar_azimuth_angle")
    if z is None or az is None:
        return None

    n = d0.dayofyear
    lat = math.radians(LAT)
    dec = math.radians(23.44) * math.sin(2 * math.pi * (284 + n) / 365)

    # hour angle of the sun from the zenith angle
    cos_h = (math.cos(math.radians(z)) - math.sin(lat) * math.sin(dec)) / (
        math.cos(lat) * math.cos(dec))
    h = math.degrees(math.acos(max(-1, min(1, cos_h))))
    if (az % 360) <= 180:                  # sun still in the east: morning
        h = -h

    # equation of time (minutes) corrects apparent to mean solar time
    b = 2 * math.pi * (n - 81) / 364
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    utc_hours = 12 + h / 15 - LON / 15 - eot / 60
    local_solar = 12 + h / 15
    return z, az, local_solar, utc_hours


def hhmm(x):
    return f"{int(x):02d}:{(round((x % 1) * 60)) % 60:02d}"


for day in ["2024-01-15", "2024-04-16", "2024-07-16", "2024-10-16"]:
    r = overpass_utc(day)
    if r is None:
        print(day, "no angle data")
        continue
    z, az, ls, utc = r
    print(f"{day}  zenith={z:5.1f}  azimuth={az:6.1f}  "
          f"local solar time={hhmm(ls)}  ->  UTC {hhmm(utc)}  (IST {hhmm(utc + 5.5)})")