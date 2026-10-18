
import ee
from .config import CFG


def init():
    try:
        ee.Initialize(project=CFG["gee_project"])
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=CFG["gee_project"])
