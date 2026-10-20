import pandas as pd
from no2.status import day_status

NUMERIC = ["no2", "valid", "cloud", "zen", "azi"]

d = pd.read_csv("data/raw/cost_test_v2_2024-01.csv",
                dtype={"cell_id": str, "date": str, "algo": str, "proc": str})
d = d.drop(columns=[c for c in (".geo", "system:index") if c in d.columns])

missing = [c for c in NUMERIC if c not in d.columns]
if missing:
    raise SystemExit(f"Export is missing columns: {missing}")

# Sentinel -> NaN immediately, so it can never be mistaken for a value
for c in NUMERIC:
    d[c] = d[c].where(d[c] != -9999)

print("Shape:", d.shape)
print("Columns:", d.columns.tolist())
print("Algorithm versions:", d["algo"].unique().tolist(),
      " Processor versions:", d["proc"].unique().tolist())
print("Cells per day (should all be 320):", d.groupby("date").size().unique().tolist())
print("Missing values per column:")
print(d[NUMERIC].isna().sum().to_string())

# --- 1. Cross-check one day against the Day 1 per-cell run ---
ref = pd.read_parquet("data/raw/inspect_2024-01-15.parquet")
e = d[d["date"] == "2024-01-15"].merge(ref[["cell_id", "no2", "valid"]],
                                       on="cell_id", suffixes=("_exp", "_ref"))
e["no2_exp_um"] = e["no2_exp"] * 1e6          # export is mol/m2, reference is umol/m2
both = e.dropna(subset=["no2_exp_um", "no2_ref"])
print("\n2024-01-15 cross-check")
print("  cells with NO2: export", int(e["no2_exp"].notna().sum()),
      " reference", int(e["no2_ref"].notna().sum()))
print("  max |NO2 difference| (umol/m2):",
      round((both["no2_exp_um"] - both["no2_ref"]).abs().max(), 6))
print("  max |valid difference|:", round((e["valid_exp"] - e["valid_ref"]).abs().max(), 6))

# --- 2. Day-level status for the whole month ---
rows = []
for date, g in d.groupby("date"):
    rows.append({"date": date, "n_granules": g["n_granules"].iloc[0],
                 "cells_with_no2": int(g["no2"].notna().sum()),
                 "valid": g["valid"].mean(), "cloud": g["cloud"].mean()})
day = pd.DataFrame(rows)
day["status"] = [day_status(n, v, c)
                 for n, v, c in zip(day["n_granules"], day["valid"], day["cloud"])]
print("\nPer-day summary:")
print(day.round(2).to_string(index=False))
print("\nStatus counts:", day["status"].value_counts().to_dict())