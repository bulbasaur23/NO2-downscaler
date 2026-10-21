import pandas as pd

new = pd.read_parquet("data/raw/no2_delhi_ncr_2024-01.parquet")
new["date"] = pd.to_datetime(new["date"])
old = pd.read_parquet("data/interim/delhi_2024-01.parquet")

m = old.merge(new, on=["cell_id", "date"], suffixes=("_old", "_new"),
              how="outer", indicator=True)
print("Row match:", m["_merge"].value_counts().to_dict())

for c in ["no2_umol", "valid", "cloud", "zen", "azi"]:
    a, b = m[c + "_old"], m[c + "_new"]
    both = a.notna() & b.notna()
    print(f"{c:9s} NaN-pattern mismatches: {int((a.isna() != b.isna()).sum()):4d}"
          f"   max abs difference: {float((a[both] - b[both]).abs().max()):.2e}")
for c in ["n_granules", "algo", "proc"]:
    print(f"{c:10s} identical:", bool((m[c + "_old"] == m[c + "_new"]).all()))