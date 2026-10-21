import pandas as pd
from .config import ROOT

PATH = ROOT / "data" / "manifest.csv"
COLS = ["region", "month", "status", "attempts", "days", "rows",
        "wall_seconds", "finished_at", "error"]


def load():
    if PATH.exists():
        return pd.read_csv(PATH, dtype=str, keep_default_na=False)
    return pd.DataFrame({c: pd.Series(dtype=str) for c in COLS})


def get(region, month):
    m = load()
    hit = m[(m["region"] == region) & (m["month"] == month)]
    return None if hit.empty else hit.iloc[0].to_dict()


def update(region, month, **fields):
    m = load()
    mask = (m["region"] == region) & (m["month"] == month)
    if not mask.any():
        row = {c: "" for c in COLS}
        row.update(region=region, month=month)
        m = pd.concat([m, pd.DataFrame([row])], ignore_index=True)
        mask = (m["region"] == region) & (m["month"] == month)
    for k, v in fields.items():
        m.loc[mask, k] = str(v)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".tmp")
    m.to_csv(tmp, index=False)
    tmp.replace(PATH)                      # atomic: never a half-written manifest