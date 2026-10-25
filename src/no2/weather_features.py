"""Weather features at each cell's own observation time (Phase 1.3c).

Pure functions on hourly arrays (index = hours since the first weather hour, UTC) plus
build_features(). Windows and interpolation share one trick: linear interpolation at
T - k hours (k = 0..K-1) has the same fractional part f for every k, so the window mean is
(1 - f) * M[i] + f * M[i + 1], with M the trailing K-hour mean on the integer hours.
"""
import numpy as np
import pandas as pd

VARS = ("u10", "v10", "t2m", "d2m", "sp", "tp", "blh")


def trailing_mean(a, k):
    """M[j] = mean(a[j-k+1 .. j]); NaN for j < k-1 and for any window containing a NaN."""
    a = np.asarray(a, float)
    bad = np.isnan(a)
    c = np.concatenate([[0.0], np.cumsum(np.where(bad, 0.0, a))])
    nb = np.concatenate([[0], np.cumsum(bad)])
    out = np.full(len(a), np.nan)
    m = (c[k:] - c[:-k]) / k
    m[(nb[k:] - nb[:-k]) > 0] = np.nan
    out[k - 1:] = m
    return out


def interp(a, T):
    """Linear interpolation of an hourly series at fractional hour indices T."""
    a = np.asarray(a, float)
    T = np.asarray(T, float)
    i = np.floor(T).astype(int)
    f = T - i
    out = a[i] * (1 - f) + a[i + 1] * f
    return np.where(f == 0, a[i], out)          # exact hour: ignore a missing next hour


def window_mean(a, T, k):
    """Mean of the series interpolated at T, T-1, ..., T-(k-1) hours."""
    m = trailing_mean(a, k)
    T = np.asarray(T, float)
    i = np.floor(T).astype(int)
    f = T - i
    out = m[i] * (1 - f) + m[i + 1] * f
    return np.where(f == 0, m[i], out)


def prev_day_mean(a, day_idx):
    """Mean over the 24 hours of the previous UTC day; day_idx = index of 00:00 of the date."""
    return trailing_mean(a, 24)[np.asarray(day_idx, int) - 1]


def rel_humidity(t_c, td_c):
    """Relative humidity (%) from temperature and dewpoint in Celsius (Magnus form)."""
    a, b = 17.625, 243.04
    rh = 100.0 * np.exp(a * td_c / (b + td_c)) / np.exp(a * t_c / (b + t_c))
    return np.clip(rh, 0.0, 100.0)


FEATURES = ["u_ovp", "v_ovp", "ws_ovp", "t_ovp_c", "rh_ovp", "sp_ovp_hpa", "precip_ovp_mm",
            "blh_ovp_m", "vent_ovp", "u_prevday", "v_prevday", "u_24h", "v_24h",
            "u_48h", "v_48h", "precip_prevday_mm"]


def build_features(weather, obs, groups):
    """weather: time (UTC), rep, u10..blh, hourly and contiguous per rep.
    obs: cell_id, date (midnight), obs_h (UTC decimal hours, NaN allowed).
    groups: cell_id, rep. Returns cell_id, date + FEATURES (NaN where obs_h is NaN)."""
    t0 = weather["time"].min()
    n = int((weather["time"].max() - t0) / pd.Timedelta(hours=1)) + 1
    series = {}
    for rep, g in weather.groupby("rep"):
        g = g.sort_values("time")
        idx = ((g["time"] - t0) / pd.Timedelta(hours=1)).round().astype(int).to_numpy()
        if len(g) != n or not np.array_equal(idx, np.arange(n)):
            raise ValueError(f"rep {rep}: hourly series has gaps or duplicates")
        s = {c: g[c].to_numpy(float) for c in VARS}
        s["tp"] = np.clip(s["tp"], 0.0, None)          # tiny negative values are noise
        series[rep] = s

    o = obs.merge(groups[["cell_id", "rep"]], on="cell_id", how="left")
    if o["rep"].isna().any():
        raise ValueError("cells without an ERA5 pixel group")
    o["day_idx"] = ((o["date"] - t0) / pd.Timedelta(hours=1)).round().astype(int)
    res = pd.DataFrame(np.nan, index=o.index, columns=FEATURES)

    for rep, rows in o.groupby("rep"):
        s = series[rep]
        T = (rows["day_idx"] + rows["obs_h"]).to_numpy(float)
        ok = np.isfinite(T)
        if not ok.any():
            continue
        Tk, D = T[ok], rows["day_idx"].to_numpy(int)[ok]
        u, v = interp(s["u10"], Tk), interp(s["v10"], Tk)
        ws = np.hypot(u, v)
        t_c, td_c = interp(s["t2m"], Tk) - 273.15, interp(s["d2m"], Tk) - 273.15
        blh = interp(s["blh"], Tk)
        vals = {
            "u_ovp": u, "v_ovp": v, "ws_ovp": ws, "t_ovp_c": t_c,
            "rh_ovp": rel_humidity(t_c, td_c), "sp_ovp_hpa": interp(s["sp"], Tk) / 100.0,
            "precip_ovp_mm": interp(s["tp"], Tk) * 1000.0, "blh_ovp_m": blh, "vent_ovp": ws * blh,
            "u_prevday": prev_day_mean(s["u10"], D), "v_prevday": prev_day_mean(s["v10"], D),
            "u_24h": window_mean(s["u10"], Tk, 24), "v_24h": window_mean(s["v10"], Tk, 24),
            "u_48h": window_mean(s["u10"], Tk, 48), "v_48h": window_mean(s["v10"], Tk, 48),
            "precip_prevday_mm": prev_day_mean(s["tp"], D) * 24.0 * 1000.0,
        }
        for name, arr in vals.items():
            col = np.full(len(rows), np.nan)
            col[ok] = arr
            res.loc[rows.index, name] = col

    return o[["cell_id", "date"]].join(res)