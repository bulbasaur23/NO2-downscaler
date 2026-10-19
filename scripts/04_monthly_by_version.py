from collections import Counter

import ee
import pandas as pd
import matplotlib.pyplot as plt
from no2.config import CFG
from no2.gee import init

init()
b = CFG["delhi_ncr"]
region = ee.Geometry.Rectangle([b["west"], b["south"], b["east"], b["north"]])
band = CFG["no2_band"]
SCALE = 1113.2


def month_feature(start_str):
    """Server-side: one row of stats for the month starting at start_str."""
    start = ee.Date(start_str)
    col = (ee.ImageCollection(CFG["no2_collection"])
           .filterDate(start, start.advance(1, "month")))
    img = col.select(band).mean()
    val = img.reduceRegion(ee.Reducer.mean(), region, SCALE, crs="EPSG:4326").get(band)
    return ee.Feature(None, {
        "month": start.format("YYYY-MM"),
        "no2": val,
        "n_granules": col.size(),
        "algos": col.aggregate_array("ALGORITHM_VERSION"),
        "procs": col.aggregate_array("PROCESSOR_VERSION"),
    })


rows = []
for year in range(2018, 2027):
    starts = [f"{year}-{m:02d}-01" for m in range(1, 13)]
    starts = [s for s in starts if "2018-07-01" <= s <= "2026-10-01"]
    if not starts:
        continue
    fc = ee.FeatureCollection(ee.List(starts).map(month_feature)).getInfo()
    rows += [f["properties"] for f in fc["features"]]
    print(year, "done")

df = pd.DataFrame(rows)
df["month"] = pd.to_datetime(df["month"])
df["no2"] = df["no2"] * 1e6                                   # umol/m2

# A month that spans two versions gets the version most granules belong to
df["algo"] = df["algos"].apply(lambda v: Counter(v).most_common(1)[0][0] if v else None)
df["proc"] = df["procs"].apply(lambda v: Counter(v).most_common(1)[0][0] if v else None)
df["mixed"] = df["algos"].apply(lambda v: len(set(v)) > 1)
df = df.drop(columns=["algos", "procs"]).sort_values("month")
df.to_parquet("data/raw/monthly_by_version.parquet", index=False)

# ---- printed summary ----
print("\nMean of monthly values by algorithm version:")
print(df.groupby("algo")["no2"].agg(["count", "mean"]).round(1).to_string())

df["year"] = df["month"].dt.year
df["m"] = df["month"].dt.month
table = df.pivot(index="m", columns="year", values="no2").round(0)
print("\nMonthly NO2 (umol/m2), rows = month, columns = year:")
print(table.to_string())

# ---- plots ----
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9))

for v, g in df.groupby("algo"):
    ax1.plot(g["month"], g["no2"], "o-", label=f"algorithm {v}")
for boundary in ("2022-07-17", "2024-11-16", "2025-11-22"):
    ax1.axvline(pd.Timestamp(boundary), color="grey", linestyle="--", linewidth=1)
ax1.set_title("Monthly mean tropospheric NO2 column, Delhi NCR box (dashed = algorithm change)")
ax1.set_ylabel("umol/m2")
ax1.legend(fontsize=8)

table.plot(ax=ax2, marker="o")
ax2.set_title("Same data, one line per year (a version step shows as a shifted year)")
ax2.set_xlabel("month")
ax2.set_ylabel("umol/m2")

plt.tight_layout()
plt.savefig("notes/version_plot.png", dpi=120)
print("\nSaved notes/version_plot.png")