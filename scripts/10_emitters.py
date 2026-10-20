import datetime
import ee
import pandas as pd
from no2.config import ROOT
from no2.gee import init

init()
ASSET = "WRI/GPPD/power_plants"
FOSSIL = ["Coal", "Gas", "Oil"]            # NOx emitters; hydro, solar, nuclear excluded

india = ee.FeatureCollection(ASSET).filter(ee.Filter.eq("country", "IND"))
n_india = india.size().getInfo()
if n_india == 0:
    raise SystemExit("No plants with country == 'IND'. Check the 'country' values.")

print("India plants (all fuels):", n_india)
print("By primary fuel:", india.aggregate_histogram("fuel1").getInfo())

fossil = india.filter(ee.Filter.inList("fuel1", FOSSIL))
rows = []
for f in fossil.getInfo()["features"]:
    p = dict(f["properties"])
    p["longitude"], p["latitude"] = f["geometry"]["coordinates"][:2]
    rows.append(p)

df = pd.DataFrame(rows).rename(columns={"capacitymw": "capacity_mw", "fuel1": "primary_fuel",
                                        "comm_year": "commissioning_year"})
keep = ["gppd_idnr", "name", "primary_fuel", "capacity_mw", "commissioning_year",
        "cap_year", "owner", "source", "latitude", "longitude"]
df = df[[c for c in keep if c in df.columns]].sort_values("capacity_mw", ascending=False)

out = ROOT / "config" / "emitters_india_fossil.csv"
df.to_csv(out, index=False)

meta = ROOT / "config" / "emitters_india_fossil.meta.txt"
meta.write_text(
    f"source asset: {ASSET}\n"
    f"pulled: {datetime.date.today().isoformat()}\n"
    f"filter: country == IND, fuel1 in {FOSSIL}\n"
    f"plants saved: {len(df)}\n"
    "note: snapshot is old (generation columns end 2016; closed plants still listed).\n"
    "      Apply config/emitters_exclude.csv before use.\n"
)
print(f"\nSaved {len(df)} fossil plants to {out}")
print(df.head(10)[["name", "primary_fuel", "capacity_mw", "commissioning_year"]].to_string(index=False))