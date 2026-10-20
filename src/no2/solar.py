"""Observation time from satellite solar angles.

Sentinel-5P's overpass time over a point varies day to day (swath position),
so we derive it from the solar zenith/azimuth angles in the data.
"""
import math


def observation_utc_hours(day_of_year, zenith, azimuth, lon, lat):
    """UTC time (decimal hours) at which the sun had this zenith/azimuth."""
    n = day_of_year
    lat_r = math.radians(lat)
    dec = math.radians(23.44) * math.sin(2 * math.pi * (284 + n) / 365)

    cos_h = (math.cos(math.radians(zenith)) - math.sin(lat_r) * math.sin(dec)) / (
        math.cos(lat_r) * math.cos(dec))
    h = math.degrees(math.acos(max(-1.0, min(1.0, cos_h))))   # hour angle, degrees
    if (azimuth % 360) <= 180:          # sun in the east: morning, before noon
        h = -h

    b = 2 * math.pi * (n - 81) / 364
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)  # minutes

    return 12 + h / 15 - lon / 15 - eot / 60


def hhmm(hours):
    total = (round(hours * 60))
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"