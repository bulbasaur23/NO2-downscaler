import datetime
import time
from . import manifest
from .pull import pull_month, write_month
from .quota_log import log
from .status import day_status


def run_month(region, month, force=False, verbose=False):
    row = manifest.get(region, month)
    if row and row["status"] == "done" and not force:
        return {"state": "skipped", "rows": row["rows"], "sec": row["wall_seconds"]}

    attempts = (int(row["attempts"]) + 1) if row and row["attempts"] else 1
    manifest.update(region, month, status="running", attempts=attempts, error="")
    t0 = time.perf_counter()
    try:
        df = pull_month(region, month, verbose=verbose)
        path = write_month(df, region, month)
    except Exception as e:
        manifest.update(region, month, status="failed", error=repr(e)[:300])
        return {"state": "failed", "error": repr(e)[:200]}

    sec = round(time.perf_counter() - t0)
    manifest.update(region, month, status="done", days=df["date"].nunique(), rows=len(df),
                    wall_seconds=sec, error="",
                    finished_at=datetime.datetime.now().isoformat(timespec="seconds"))
    log(f"pull {region} {month}", sec, None, "interactive per-day pulls")

    day = df.groupby("date").agg(n=("n_granules", "first"),
                                 valid=("valid", "mean"), cloud=("cloud", "mean"))
    st = [day_status(n, v, c) for n, v, c in zip(day["n"], day["valid"], day["cloud"])]
    return {"state": "done", "rows": len(df), "sec": sec, "path": str(path),
            "status_counts": {s: st.count(s) for s in sorted(set(st))}}