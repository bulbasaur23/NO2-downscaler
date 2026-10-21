import re
import sys
from no2.gee import init
from no2.runner import run_month

# Usage: python scripts/20_pull_month.py 2024-01 [--force]
REGION = "delhi_ncr"
month = sys.argv[1]
if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
    sys.exit(f"Month must look like 2024-01, got {month!r}")

init()
print(run_month(REGION, month, force="--force" in sys.argv, verbose=True))