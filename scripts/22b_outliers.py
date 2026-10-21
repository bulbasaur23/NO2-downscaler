import pandas as pd
from pathlib import Path

files = sorted(Path("data/raw").glob("no2_delhi_ncr_*.parquet"))
d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
d["date"] = pd.to_datetime(d["date"])
x = d[d["no2_umol"].notna()].copy()
x["month"] = x["date"].dt.month

print("Quantiles of cell-day NO2 (umol/m2):")
print(x["no2_umol"].quantile([0.001, 0.01, 0.5, 0.99, 0.999, 0.9999]).round(1).to_string())

neg = x[x["no2_umol"] < 0]
print(f"\nNegative cell-days: {len(neg)}")
print("  by calendar month:", neg["month"].value_counts().sort_index().to_dict())
print("  valid fraction: median", round(neg["valid"].median(), 2),
      "| share with valid >= 0.5:", round((neg["valid"] >= 0.5).mean(), 2))
print("  distinct cells:", neg["cell_id"].nunique(), "| distinct days:", neg["date"].nunique())
print(neg.nsmallest(5, "no2_umol")[["date", "cell_id", "no2_umol", "valid", "cloud"]]
      .round(2).to_string(index=False))

top = x.nlargest(100, "no2_umol")
print("\nLargest values:")
print(top.head(12)[["date", "cell_id", "no2_umol", "valid", "cloud"]].round(2).to_string(index=False))
print("  top 100: share with valid < 0.5:", round((top["valid"] < 0.5).mean(), 2))
print("  top 100 by calendar month:", top["month"].value_counts().sort_index().to_dict())
print("  top 100: distinct days:", top["date"].nunique(), "| distinct cells:", top["cell_id"].nunique())