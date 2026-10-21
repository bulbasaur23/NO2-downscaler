import pandas as pd
from pathlib import Path
from no2 import manifest
from no2.status import day_status

REGION = "delhi_ncr"
expected_months = [p.strftime("%Y-%m") for p in pd.period_range("2022-07", "2026-09", freq="M")]

# --- 1. Manifest ---
m = manifest.load()
m = m[m["region"] == REGION]
print("Manifest states:", m["status"].value_counts().to_dict())
not_done = sorted(set(expected_months) - set(m.loc[m["status"] == "done", "month"]))
print("Months not done:", not_done if not_done else "none")

# --- 2. Read every file back ---
files = sorted(Path("data/raw").glob(f"no2_{REGION}_*.parquet"))
d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
d["date"] = pd.to_datetime(d["date"])
n_days = (pd.Timestamp("2026-09-30") - pd.Timestamp("2022-07-01")).days + 1
print(f"\nFiles: {len(files)} (expected {len(expected_months)})")
print(f"Rows: {len(d):,}  expected: {n_days * 320:,} ({n_days} days x 320)")
print("Cells per day:", sorted(d.groupby("date").size().unique().tolist()))
print("Duplicate cell-days:", int(d.duplicated(["cell_id", "date"]).sum()))

# --- 3. Values ---
x = d["no2_umol"].dropna()
print(f"\nNO2 (umol/m2), {len(x):,} cell-days with a value:")
print("  min", round(x.min(), 1), " median", round(x.median(), 1), " max", round(x.max(), 1))
print("  negatives:", int((x < 0).sum()), " below 20:", int((x < 20).sum()))

# --- 4. One row per day ---
day = d.groupby("date").agg(
    n=("n_granules", "first"), valid=("valid", "mean"), cloud=("cloud", "mean"),
    algo=("algo", "first"), proc=("proc", "first"),
    obs50=("valid", lambda s: int((s >= 0.5).sum()))).reset_index()
day["status"] = [day_status(n, v, c) for n, v, c in zip(day["n"], day["valid"], day["cloud"])]

# --- 5. Version labels ---
print("\nAlgorithm labels (by day):")
print(day.groupby("algo")["date"].agg(["min", "max", "count"]).to_string())
mixed = day[day["algo"].str.contains(",") | (day["algo"] == "")]
print("Days with a mixed or empty algorithm label:", len(mixed),
      list(mixed["date"].dt.strftime("%Y-%m-%d")))
print("\nDay status by algorithm label:")
print(pd.crosstab(day["algo"], day["status"]).to_string())
late = day[day["date"] >= "2025-11-22"]
print(f"\nFrom 2025-11-22 (version-shift test): {len(late)} days,",
      late["status"].value_counts().to_dict())

# --- 6. Season preview of the valid-pixel report (Step 1.6 does this properly) ---
season_of = {12: "winter", 1: "winter", 2: "winter", 3: "pre-monsoon", 4: "pre-monsoon",
             5: "pre-monsoon", 6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon",
             10: "post-monsoon", 11: "post-monsoon"}
day["season"] = day["date"].dt.month.map(season_of)
s = day.groupby("season").agg(days=("date", "count"), mean_valid=("valid", "mean"),
                              cell_days_observed=("obs50", "mean"))
s["observed_days_share"] = day.groupby("season")["status"].apply(lambda t: (t == "observed").mean())
s["cell_days_observed"] = s["cell_days_observed"] / 320
print("\nBy season:")
print(s.round(2).to_string())
by_month = day.groupby(day["date"].dt.month)["status"].apply(lambda t: round((t == "observed").mean(), 2))
print("\nShare of days observed, by calendar month (all years):")
print(by_month.to_string())

# --- 7. no_overpass vs archive holes (granule counts below 13) ---
holes = pd.read_csv("notes/archive_holes.csv", parse_dates=["date"])
nop = day.loc[day["status"] == "no_overpass", "date"]
inwin = holes[(holes["date"] >= "2022-07-01") & (holes["date"] <= "2026-09-30")]
print(f"\nno_overpass days: {len(nop)}")
print(f"Short days (<13 granules) inside the window: {len(inwin)}, of which no_overpass: "
      f"{int(inwin['date'].isin(nop).sum())}")
not_short = nop[~nop.isin(holes["date"])]
print("no_overpass days that were NOT short:", list(not_short.dt.strftime("%Y-%m-%d")))