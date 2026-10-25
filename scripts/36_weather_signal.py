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

t = x[x["no2_umol"].notna()]
print("Cell-days with a NO2 value, by observation-time source:", t["obs_src"].value_counts().to_dict())

obs = x[x["valid"] >= 0.5]
day = obs.groupby("date").agg(no2=("no2_umol", "mean"), cells=("cell_id", "size"),
                              blh=("blh_ovp_m", "mean"), ws=("ws_ovp", "mean"),
                              vent=("vent_ovp", "mean"), ws24=("ws24", "mean"),
                              rain=("precip_prevday_mm", "mean"))
day = day[day["cells"] >= 100].copy()
day["month"] = day.index.month
season = {12: "winter", 1: "winter", 2: "winter", 3: "pre-monsoon", 4: "pre-monsoon",
          5: "pre-monsoon", 6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon",
          10: "post-monsoon", 11: "post-monsoon"}
day["season"] = day["month"].map(season)


def rho(a, b):
    return a.rank().corr(b.rank())


print(f"\nRank correlation of daily mean NO2 with weather ({len(day)} days with >= 100 observed cells):")
rows = [{"season": s, "days": len(g), **{c: rho(g["no2"], g[c]) for c in ("blh", "ws", "vent", "ws24", "rain")}}
        for s, g in day.groupby("season")]
rows.append({"season": "all", "days": len(day), **{c: rho(day["no2"], day[c]) for c in ("blh", "ws", "vent", "ws24", "rain")}})
print(pd.DataFrame(rows).round(2).to_string(index=False))

# --- the extreme-value days from step 1.2 ---
top = pd.DatetimeIndex(d.nlargest(100, "no2_umol")["date"].unique())
ex = day.loc[day.index.intersection(top)]
cmp_ = day[day["month"].isin([11, 12, 1, 2])]
print(f"\nExtreme-value days (top 100 cell values): {len(top)} days, {len(ex)} with >= 100 observed cells")
for c in ("vent", "blh", "ws"):
    pct = ex[c].apply(lambda v: (cmp_[c] < v).mean())
    print(f"  {c:5s} percentile among {len(cmp_)} Nov-Feb days: median {pct.median():.2f}, "
          f"range {pct.min():.2f}-{pct.max():.2f}, below 0.25 on {int((pct < 0.25).sum())} of {len(pct)} days")

# --- day-to-day jumps ---
dd = day.sort_index()
prev = dd.shift(1)
consecutive = (dd.index.to_series().diff().dt.days == 1).to_numpy()
mask = ((dd["no2"] / prev["no2"] > 1.8).to_numpy() & consecutive
        & (dd["cells"] >= 200).to_numpy() & (prev["cells"] >= 200).to_numpy())
out = pd.DataFrame({"no2_prev": prev["no2"], "no2": dd["no2"], "blh_prev": prev["blh"], "blh": dd["blh"],
                    "vent_prev": prev["vent"], "vent": dd["vent"]})[mask]
print(f"\nDays where mean NO2 rose by more than 1.8x (both days >= 200 observed cells): {len(out)}")
if len(out):
    print(out.round(0).to_string())
    print("Share of these days with lower ventilation than the day before:",
          round(float((out["vent"] < out["vent_prev"]).mean()), 2))