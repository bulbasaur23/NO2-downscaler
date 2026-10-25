import numpy as np
import pandas as pd
from no2.config import ROOT

RAW, INTERIM = ROOT / "data" / "raw", ROOT / "data" / "interim"
d = pd.concat([pd.read_parquet(f, columns=["cell_id", "date", "no2_umol", "valid"])
               for f in sorted(RAW.glob("no2_delhi_ncr_*.parquet"))], ignore_index=True)
d["date"] = pd.to_datetime(d["date"])
f = pd.read_parquet(INTERIM / "weather_features_delhi.parquet")
f["date"] = pd.to_datetime(f["date"])
x = d.merge(f, on=["cell_id", "date"], how="left")
x["ws24"] = np.hypot(x["u_24h"], x["v_24h"])

obs = x[x["valid"] >= 0.5]
day = obs.groupby("date").agg(no2=("no2_umol", "mean"), cells=("cell_id", "size"),
                              blh=("blh_ovp_m", "mean"), ws=("ws_ovp", "mean"),
                              vent=("vent_ovp", "mean"), ws24=("ws24", "mean"),
                              rain=("precip_prevday_mm", "mean"))
day = day[day["cells"] >= 100].copy()
day["ym"] = day.index.to_period("M")
day["month"] = day.index.month

cols = ["blh", "ws", "vent", "ws24", "rain"]


def rho(a, b):
    return a.rank().corr(b.rank())


rows = [{"month": g["month"].iloc[0], **{c: rho(g["no2"], g[c]) for c in cols}}
        for _, g in day.groupby("ym") if len(g) >= 8]
r = pd.DataFrame(rows)
print(f"Within-month rank correlation with daily mean NO2 ({len(r)} year-months with >= 8 days).")
print("Median across years, by calendar month:")
out = r.groupby("month")[cols].median().round(2)
out["year_months"] = r.groupby("month").size()
print(out.to_string())
print("\nMedian over all year-months:", r[cols].median().round(2).to_dict())
print("Share of year-months with a negative correlation:",
      {c: round(float((r[c] < 0).mean()), 2) for c in cols})