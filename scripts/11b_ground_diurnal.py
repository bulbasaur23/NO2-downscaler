import pandas as pd

d = pd.read_csv("data/raw/ground_ito_2024-25.csv")
t = pd.to_datetime(d["Timestamp"], format="ISO8601", utc=True, errors="coerce")
print("Rows:", len(d), " unparsed timestamps:", int(t.isna().sum()))
print("Time range:", t.min(), "->", t.max())
print("Duplicate timestamps:", int(t.duplicated().sum()))

d["t"] = t
d = d.dropna(subset=["t"]).copy()
d["hour"] = d["t"].dt.hour
d["month"] = d["t"].dt.to_period("M")

no2, sr, at = "NO2 (µg/m³)", "SR (W/mt2)", "AT (°C)"
print("\nRows per month (a full 15-minute month is about 2,900):")
print(d.groupby("month").size().to_string())
print("\nNO2 readings present per month:")
print(d.groupby("month")[no2].count().to_string())

prof = d.groupby("hour").agg(no2_median=(no2, "median"),
                             sr_median=(sr, "median"), sr_n=(sr, "count"),
                             at_median=(at, "median"), at_n=(at, "count"))
print("\nProfile by hour of the timestamp as written:")
print(prof.round(1).to_string())