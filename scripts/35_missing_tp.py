import pandas as pd
from pathlib import Path

w = pd.concat([pd.read_parquet(f) for f in sorted(Path("data/raw").glob("era5_delhi_ncr_*.parquet"))],
              ignore_index=True)
miss = w[w["tp"].isna()]
by_time = miss.groupby("time")["rep"].nunique()
print("Missing tp rows:", len(miss), "| distinct hours:", len(by_time))
print("Pixels missing per affected hour:", by_time.value_counts().to_dict())
print("Other variables missing in those rows:",
      int(miss[["u10", "v10", "t2m", "d2m", "sp", "blh"]].isna().sum().sum()))
print("\nAffected hours (UTC):")
print(by_time.index.strftime("%Y-%m-%d %H:%M").tolist())
print("Distinct calendar days:", by_time.index.normalize().nunique())
print("Hours of day:", sorted(by_time.index.hour.unique().tolist()))

mean_tp = w.groupby("time")["tp"].mean()
for t in by_time.index[:4]:
    print(f"\n{t}: previous hour tp {mean_tp.get(t - pd.Timedelta(hours=1))}, "
          f"next hour tp {mean_tp.get(t + pd.Timedelta(hours=1))}")