import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from no2.versions import normalize_processor_version

NUMERIC = ["no2", "valid", "cloud", "zen", "azi"]

d = pd.read_csv("data/raw/cost_test_v2_2024-01.csv",
                dtype={"cell_id": str, "date": str, "algo": str, "proc": str})
d = d.drop(columns=[c for c in (".geo", "system:index") if c in d.columns])
for c in NUMERIC:
    d[c] = d[c].where(d[c] != -9999)          # sentinel -> NaN

d["no2_umol"] = d["no2"] * 1e6                # mol/m2 -> umol/m2
d = d.drop(columns="no2")
d["date"] = pd.to_datetime(d["date"])
d["proc_norm"] = d["proc"].apply(normalize_processor_version)

# --- D2: observed-cell rule at three thresholds ---
for thr in (0.3, 0.5, 0.7):
    d[f"obs_{int(thr * 100)}"] = d["valid"] >= thr

print("D2 sensitivity over the month (cell-days):")
for thr in (30, 50, 70):
    o = d[d[f"obs_{thr}"]]
    print(f"  >= {thr}% coverage: observed {len(o):5d} of {len(d)} "
          f"({len(o) / len(d):.1%}), mean NO2 {o['no2_umol'].mean():.1f} umol/m2")

has_value = d["no2_umol"].notna()
partial = has_value & (d["valid"] < 0.5)
print(f"\nCell-days with a NO2 value but under 50% coverage: {int(partial.sum())}"
      f"  (mean NO2 {d.loc[partial, 'no2_umol'].mean():.1f} vs "
      f"{d.loc[d['obs_50'], 'no2_umol'].mean():.1f} for observed cells)")

# --- Which days have partial angle coverage (swath edges)? ---
miss = d.groupby("date")["zen"].apply(lambda s: int(s.isna().sum()))
print("\nDays where some, but not all, cells lack solar angles:")
print(miss[(miss > 0) & (miss < 320)].to_string())

# --- Save as Parquet with file-level metadata ---
table = pa.Table.from_pandas(d, preserve_index=False)
meta = {
    b"source": b"COPERNICUS/S5P/OFFL/L3_NO2 via Google Earth Engine",
    b"no2_units": b"umol/m2, tropospheric NO2 column (retrieved product, not surface NO2)",
    b"grid": b"0.05 degree, cell_id = iy_ix (see no2.grid)",
    b"aggregation": b"mean of the day's granules, native scale 1113.2 m, EPSG:4326",
    b"valid": b"fraction of cell area with a valid NO2 pixel (D2)",
    b"missing": b"NaN. Export sentinel -9999 converted on load",
    b"study_area": b"Delhi NCR box 76.80-77.80E, 28.20-29.00N (320 cells)",
}
table = table.replace_schema_metadata({**(table.schema.metadata or {}), **meta})
pq.write_table(table, "data/interim/delhi_2024-01.parquet")
print("\nSaved data/interim/delhi_2024-01.parquet", d.shape)