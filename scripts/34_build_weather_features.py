import numpy as np
import pandas as pd
from no2.config import CFG, ROOT
from no2.grid import cells_in_bbox
from no2.solar import observation_utc_hours
from no2.weather_features import FEATURES, build_features
from no2.weather_pull import GROUPS

RAW, INTERIM = ROOT / "data" / "raw", ROOT / "data" / "interim"
b = CFG["delhi_ncr"]
cells = cells_in_bbox(b["west"], b["south"], b["east"], b["north"])[["cell_id", "lon", "lat"]]

# --- per-cell observation time from the stored solar angles ---
d = pd.concat([pd.read_parquet(f, columns=["cell_id", "date", "zen", "azi"])
               for f in sorted(RAW.glob("no2_delhi_ncr_*.parquet"))], ignore_index=True)
d["date"] = pd.to_datetime(d["date"])
a = d.merge(cells, on="cell_id", how="left")
has = (a["zen"].notna() & a["azi"].notna()).to_numpy()
doy = a["date"].dt.dayofyear.to_numpy()
obs_h = np.full(len(a), np.nan)
obs_h[has] = [observation_utc_hours(n, z, az, lo, la) for n, z, az, lo, la in zip(
    doy[has], a["zen"].to_numpy()[has], a["azi"].to_numpy()[has],
    a["lon"].to_numpy()[has], a["lat"].to_numpy()[has])]
a["obs_h"] = obs_h
day_med = a.groupby("date")["obs_h"].transform("median")
a["obs_src"] = np.where(has, "cell", np.where(day_med.notna(), "day_median", "none"))
a["obs_h"] = a["obs_h"].fillna(day_med)
obs = a[["cell_id", "date", "obs_h", "obs_src"]].reset_index(drop=True)

w = pd.concat([pd.read_parquet(f) for f in sorted(RAW.glob("era5_delhi_ncr_*.parquet"))],
              ignore_index=True)
groups = pd.read_parquet(GROUPS)[["cell_id", "rep"]]

feats = build_features(w, obs[["cell_id", "date", "obs_h"]], groups)
feats["obs_h"] = obs["obs_h"].to_numpy()
feats["obs_src"] = obs["obs_src"].to_numpy()
feats.to_parquet(INTERIM / "weather_features_delhi.parquet", index=False)

print("Rows:", len(feats), "| observation time source:", feats["obs_src"].value_counts().to_dict())
print("Cell-days with no features (NaN):", int(feats["blh_ovp_m"].isna().sum()),
      "| without an observation time:", int(feats["obs_h"].isna().sum()))
extra = feats[FEATURES].isna().sum() - int(feats["obs_h"].isna().sum())
print("\nMissing feature values beyond the rows without an observation time:")
print(extra[extra != 0].to_string() if (extra != 0).any() else "none")
print("\nFeature ranges:")
print(feats[FEATURES].describe().loc[["min", "50%", "max"]].round(2).T.to_string())
print("\nMean BLH at the overpass by calendar month (m):",
      feats.groupby(feats["date"].dt.month)["blh_ovp_m"].mean().round(0).to_dict())

# --- spot check one row against a by-hand interpolation ---
r = feats[(feats["date"] == pd.Timestamp("2024-01-15")) & feats["obs_h"].notna()].iloc[0]
rep = int(groups.set_index("cell_id").loc[r["cell_id"], "rep"])
h0 = int(np.floor(r["obs_h"]))
fr = r["obs_h"] - h0
t_h0 = pd.Timestamp("2024-01-15") + pd.Timedelta(hours=h0)
ww = w[w["rep"] == rep].set_index("time")
by_hand = ww.loc[t_h0, "blh"] * (1 - fr) + ww.loc[t_h0 + pd.Timedelta(hours=1), "blh"] * fr
print(f"\nSpot check {r['cell_id']}, 2024-01-15, obs {r['obs_h']:.3f} UTC: "
      f"BLH feature {r['blh_ovp_m']:.2f}, by hand {by_hand:.2f}")

# --- how much does per-cell timing matter? (vs one median time per day) ---
day_obs = obs[["cell_id", "date"]].assign(obs_h=obs.groupby("date")["obs_h"].transform("median").to_numpy())
feats_day = build_features(w, day_obs, groups)
rel = ((feats["blh_ovp_m"] - feats_day["blh_ovp_m"]).abs() / feats_day["blh_ovp_m"]).to_numpy()
flag = pd.read_parquet(INTERIM / "obs_time_delhi.parquet")[["date", "flag"]]
flag["date"] = pd.to_datetime(flag["date"])
t = feats[["date"]].assign(rel=rel).merge(flag, on="date", how="left")
print("\nRelative BLH difference, per-cell time vs one time per day (by flagged day):")
print(t.groupby("flag")["rel"].describe(percentiles=[0.5, 0.95]).round(3).to_string())