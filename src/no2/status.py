"""Day-level status for a region (plan decision D6).

no_overpass  : no usable product covers the region (not cloud, not an error)
insufficient : product exists but too little valid area
observed     : enough valid area
"""
import pandas as pd


def day_status(n_images, valid_frac, cloud_frac, min_valid=0.5):
    cloud_missing = cloud_frac is None or pd.isna(cloud_frac)
    valid = 0.0 if valid_frac is None or pd.isna(valid_frac) else valid_frac

    if not n_images:
        return "no_overpass"
    if cloud_missing and valid == 0:
        return "no_overpass"
    if valid >= min_valid:
        return "observed"
    return "insufficient"