import pandas as pd

URL = ("https://data.opencity.in/dataset/0dc7b9fe-9fd4-46ee-a37e-88f0bd6f6362/"
       "resource/890f786d-fb9f-475e-8516-191bfa1b01ea/download/del-ito-cpcb-2024-25.csv")

df = pd.read_csv(URL)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
print(df.head(3).to_string())

date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
no2_cols = [c for c in df.columns if "no2" in c.lower()]
print("\nCandidate time columns:", date_cols)
print("Candidate NO2 columns:", no2_cols)

if date_cols:
    t = pd.to_datetime(df[date_cols[0]], errors="coerce", dayfirst=True)
    print("Time range:", t.min(), "->", t.max(), " unparsed:", int(t.isna().sum()))
for c in no2_cols:
    x = pd.to_numeric(df[c], errors="coerce")
    print(f"{c}: non-missing {int(x.notna().sum())} of {len(x)}, "
          f"min {x.min()}, median {x.median()}, max {x.max()}")

df.to_csv("data/raw/ground_ito_2024-25.csv", index=False)
print("\nSaved data/raw/ground_ito_2024-25.csv")