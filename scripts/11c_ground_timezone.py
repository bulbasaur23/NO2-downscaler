import pandas as pd

BASE = "https://data.opencity.in/dataset/0dc7b9fe-9fd4-46ee-a37e-88f0bd6f6362/resource/"
FILES = {
    "Sirifort": BASE + "e562d0c9-cc37-4d5a-a04e-fd95ee9f2f04/download/del-sirifort-cpcb-2024-25.csv",
    "Shadipur": BASE + "e91c68ea-85ac-49f8-8015-dd8b04c32a71/download/del-shadipur-cpcb-2024-25.csv",
}
NO2, SR, AT = "NO2 (µg/m³)", "SR (W/mt2)", "AT (°C)"

for name, url in FILES.items():
    print("=" * 60, "\n", name)
    d = pd.read_csv(url)
    d["t"] = pd.to_datetime(d["Timestamp"], format="ISO8601", utc=True, errors="coerce")
    d = d.dropna(subset=["t"]).copy()
    d["hour"] = d["t"].dt.hour
    print("Rows:", len(d), " range:", d["t"].min(), "->", d["t"].max())
    for c in (NO2, SR, AT):
        print(f"  {c}:", f"present {int(d[c].notna().sum())}" if c in d.columns else "column missing")

    g = d.groupby("hour")
    if SR in d.columns and d[SR].notna().sum() > 0:
        sr = g[SR].median()
        print("  SR median peaks at hour:", int(sr.idxmax()), " value", round(sr.max(), 1))
        print("  SR median by hour:", sr.round(0).to_dict())
    if AT in d.columns and d[AT].notna().sum() > 0:
        print("  AT median peaks at hour:", int(g[AT].median().idxmax()))
    if NO2 in d.columns:
        n = g[NO2].median()
        print("  NO2 median lowest at hour:", int(n.idxmin()), " highest at hour:", int(n.idxmax()))