import pandas as pd
from pathlib import Path

files = sorted(Path("data/raw").glob("no2_delhi_ncr_*.parquet"))
d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
d["date"] = pd.to_datetime(d["date"])
obs = d[d["valid"] >= 0.5]
sat = obs.groupby("date").agg(sat=("no2_umol", "mean"), cells=("cell_id", "size"))
sat = sat[sat["cells"] >= 100]["sat"]

g = pd.read_csv("data/raw/ground_ito_2024-25.csv")
g["t"] = pd.to_datetime(g["Timestamp"], format="ISO8601", utc=True,
                        errors="coerce").dt.tz_localize(None)       # as-written (IST) clock
g = g.dropna(subset=["t"])
noon = g[g["t"].dt.hour.between(12, 14)]
ito = noon.groupby(noon["t"].dt.normalize())["NO2 (µg/m³)"].mean().rename("ito")
ito24 = g.groupby(g["t"].dt.normalize())["NO2 (µg/m³)"].mean().rename("ito_24h")

j = pd.concat([sat, ito, ito24], axis=1, join="inner").dropna()
j["month"] = j.index.to_period("M")
mm = j.groupby("month")[["sat", "ito", "ito_24h"]].mean()
mm["n_days"] = j.groupby("month").size()
print("Monthly means (satellite umol/m2; ITO ug/m3):")
print(mm.round(1).to_string())
def sp(a, b):
    return a.rank().corr(b.rank())      # Spearman without scipy
print("\nSpearman of the monthly means:  sat vs ITO 12-14h:",
      round(sp(mm["sat"], mm["ito"]), 2),
      "  sat vs ITO 24h:", round(sp(mm["sat"], mm["ito_24h"]), 2))

w = j.groupby("month")[["sat", "ito"]].apply(
    lambda x: sp(x["sat"], x["ito"]) if len(x) >= 8 else float("nan"))
print("\nWithin-month daily Spearman (months with >= 8 days): median", round(w.median(), 2),
      " range", round(w.min(), 2), "to", round(w.max(), 2),
      " positive in", int((w > 0).sum()), "of", int(w.notna().sum()), "months")

for lag in (-1, 1):
    i2 = j["ito"].copy()
    i2.index = i2.index + pd.Timedelta(days=lag)
    jj = pd.concat([j["sat"], i2], axis=1, join="inner").dropna()
    print(f"ITO shifted {lag:+d} day: Spearman {jj.corr(method='spearman').iloc[0, 1]:+.2f}  n={len(jj)}")