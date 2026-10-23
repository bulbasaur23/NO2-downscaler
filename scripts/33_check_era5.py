import pandas as pd
from pathlib import Path
from no2 import manifest
from no2.weather_pull import SHORT, GROUPS

files = sorted(Path("data/raw").glob("era5_delhi_ncr_*.parquet"))
w = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
m = manifest.load()
m = m[m["region"] == "era5_delhi_ncr"]
print("Manifest states:", m["status"].value_counts().to_dict(), "| files:", len(files))

n_rep = w["rep"].nunique()
hours = pd.date_range(w["time"].min(), w["time"].max(), freq="h")
print(f"Rows: {len(w):,}  pixels: {n_rep}  range: {w['time'].min()} -> {w['time'].max()}")
print(f"Expected rows: {len(hours) * n_rep:,}  duplicates: {int(w.duplicated(['time', 'rep']).sum())}")
print("Missing values per column:")
print(w[SHORT].isna().sum().to_string())

v = pd.DataFrame({"u10 m/s": w.u10, "v10 m/s": w.v10, "t2m C": w.t2m - 273.15,
                  "d2m C": w.d2m - 273.15, "sp hPa": w.sp / 100,
                  "tp mm/h": w.tp * 1000, "blh m": w.blh})
print("\nRanges:")
print(v.describe().loc[["min", "50%", "max"]].round(2).T.to_string())

h = w["time"].dt.hour
print("\nMean precipitation by UTC hour (mm per hour): flat = per-hour values;",
      "rising through the day = accumulation since 00 UTC")
print((w.groupby(h)["tp"].mean() * 1000).round(3).to_dict())
print("\nMean BLH by UTC hour (m):",
      (w.groupby(h)["blh"].mean().round(0).loc[[2, 5, 8, 11, 14, 20]]).to_dict())

d = w.assign(day=w["time"].dt.floor("D")).groupby(["day", "rep"])["tp"].sum() * 1000
mm = d.groupby(d.index.get_level_values("day").month).mean().round(2)
print("\nMean daily precipitation by calendar month (mm/day):", mm.to_dict())

g = pd.read_parquet(GROUPS).drop_duplicates("rep").set_index("rep")
s = w[w["time"] == pd.Timestamp("2024-01-15 08:00")].set_index("rep")
print("\nConsistency with the pixel-mapping sample (2024-01-15 08:00 UTC):")
if len(s):
    for a, b in (("u10", "sig_u10"), ("v10", "sig_v10"), ("t2m", "sig_t2m")):
        print(f"  max |pulled - sampled| {a}: {float((s[a] - g[b]).abs().max()):.2e}")
else:
    print("  2024-01 not pulled yet: skipped")