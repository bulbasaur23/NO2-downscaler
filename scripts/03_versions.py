import ee
import pandas as pd
from no2.config import CFG
from no2.gee import init

init()

months = pd.date_range("2018-07-01", "2026-10-01", freq="MS")
frames = []

for start in months:
    end = start + pd.offsets.MonthBegin(1)
    col = (ee.ImageCollection(CFG["no2_collection"])
           .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))

    res = ee.Dictionary({
        "t": col.aggregate_array("system:time_start"),
        "proc": col.aggregate_array("PROCESSOR_VERSION"),
        "algo": col.aggregate_array("ALGORITHM_VERSION"),
    }).getInfo()

    frames.append(pd.DataFrame(res))
    print(start.strftime("%Y-%m"), len(res["t"]), "granules")

df = pd.concat(frames, ignore_index=True)
df["time"] = pd.to_datetime(df["t"], unit="ms")
df = df.drop(columns="t").sort_values("time")
df.to_parquet("data/raw/versions.parquet", index=False)

print("\nFirst and last date:", df["time"].min(), "->", df["time"].max())
print("\nProcessor versions:")
print(df.groupby("proc")["time"].agg(["min", "max", "count"]).sort_values("min").to_string())
print("\nAlgorithm versions:")
print(df.groupby("algo")["time"].agg(["min", "max", "count"]).sort_values("min").to_string())
print("\nGranules per year:")
print(df.groupby(df["time"].dt.year).size().to_string())