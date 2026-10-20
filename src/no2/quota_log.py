import csv
from datetime import datetime
from .config import ROOT

LOG = ROOT / "notes" / "quota_log.csv"


def log(label, wall_seconds=None, eecu_seconds=None, note=""):
    new = not LOG.exists()
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "label", "wall_seconds", "eecu_seconds", "note"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), label,
                    wall_seconds, eecu_seconds, note])