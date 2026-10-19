import pandas as pd

df = pd.read_parquet("data/raw/versions.parquet")

per_day = df.groupby(df["time"].dt.date).size().rename("granules")
per_day.index = pd.to_datetime(per_day.index)

# Every calendar day in the range, so days with no granules at all show as 0
full = pd.date_range(per_day.index.min(), per_day.index.max(), freq="D")
per_day = per_day.reindex(full, fill_value=0)

short = per_day[per_day < 13]
print("Typical granules per day:", int(per_day.median()))
print(f"Days with fewer than 13 granules: {len(short)} of {len(per_day)}")

print("\nBy month (months with at least one short day):")
summary = (short.groupby(short.index.to_period("M"))
           .agg(["count", "min"])
           .rename(columns={"count": "short_days", "min": "fewest"}))
print(summary.to_string())

print("\nDays with zero granules:",
      list(per_day[per_day == 0].index.strftime("%Y-%m-%d")))

short_df = short.rename("granules").reset_index().rename(columns={"index": "date"})
short_df["in_algo_1_6_to_1_7"] = (short_df["date"] >= "2022-07-17") & (short_df["date"] < "2025-11-22")
short_df["after_1_8_start"] = short_df["date"] >= "2025-11-22"
short_df.to_csv("notes/archive_holes.csv", index=False)
print("\nSaved notes/archive_holes.csv")