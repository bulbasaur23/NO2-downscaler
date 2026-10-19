"""Processor-version handling (plan decision D3).

The label format changed in late 2025 ('2.8.0' -> '02.09.01'), and a one-off
development label ('03.00.DV') exists. Compare versions as integer tuples,
never as text.
"""
import re

_STANDARD = re.compile(r"^\d+\.\d+\.\d+$")


def parse_processor_version(v):
    """'2.8.0' -> (2, 8, 0); '02.09.01' -> (2, 9, 1); non-standard -> None."""
    if v is None:
        return None
    v = str(v).strip()
    if not _STANDARD.match(v):
        return None
    return tuple(int(p) for p in v.split("."))


def normalize_processor_version(v):
    """Canonical text form, e.g. '02.09.01' -> '2.9.1'. None if non-standard."""
    t = parse_processor_version(v)
    return None if t is None else ".".join(str(p) for p in t)