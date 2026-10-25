import numpy as np
import pandas as pd
import pytest

from no2.weather_features import (FEATURES, build_features, interp, prev_day_mean,
                                  rel_humidity, trailing_mean, window_mean)


def test_interp_between_hours():
    a = np.arange(0, 100, 10.0)                      # 0, 10, 20, ...
    assert interp(a, 2.5) == pytest.approx(25.0)
    assert interp(a, 3.0) == pytest.approx(30.0)


def test_window_mean_24h_on_a_ramp():
    a = np.arange(200.0)                             # a[j] = j
    # values at 100.5, 99.5, ..., 77.5 -> mean 89.0
    assert window_mean(a, 100.5, 24) == pytest.approx(89.0)


def test_window_mean_48h_on_integer_hour():
    a = np.arange(200.0)
    assert window_mean(a, 100.0, 48) == pytest.approx(76.5)


def test_trailing_mean_is_nan_before_a_full_window():
    m = trailing_mean(np.arange(30.0), 24)
    assert np.isnan(m[22]) and not np.isnan(m[23])


def test_previous_day_mean_picks_the_right_day():
    a = (np.arange(24 * 6) // 24).astype(float)      # value = day number 0..5
    assert prev_day_mean(a, 24 * 3) == pytest.approx(2.0)   # date = day 3 -> previous day 2


def test_relative_humidity():
    assert rel_humidity(25.0, 25.0) == pytest.approx(100.0)
    assert rel_humidity(30.0, 20.0) == pytest.approx(55.1, abs=1.0)


def _synthetic():
    """Four days of hourly weather, 2 pixels. u10 = hour of day, v10 = day number,
    tp = 0.001 m every hour, blh = 100 * hour of day."""
    t = pd.date_range("2024-01-01", periods=24 * 4, freq="h")
    frames = []
    for rep in (0, 1):
        frames.append(pd.DataFrame({
            "time": t, "rep": rep, "u10": t.hour.astype(float) + rep,
            "v10": (np.arange(len(t)) // 24).astype(float), "t2m": 290.0, "d2m": 285.0,
            "sp": 99000.0, "tp": 0.001, "blh": 100.0 * t.hour}))
    return pd.concat(frames, ignore_index=True)


def test_time_alignment_utc_hour_of_day():
    """Date 2024-01-03 at 08:30 UTC: u10 (= hour of day) interpolates to 8.5."""
    w = _synthetic()
    obs = pd.DataFrame({"cell_id": ["a"], "date": [pd.Timestamp("2024-01-03")], "obs_h": [8.5]})
    groups = pd.DataFrame({"cell_id": ["a"], "rep": [0]})
    f = build_features(w, obs, groups)
    assert f["u_ovp"].iloc[0] == pytest.approx(8.5)
    assert f["blh_ovp_m"].iloc[0] == pytest.approx(850.0)
    assert f["v_prevday"].iloc[0] == pytest.approx(1.0)        # previous day of day 2 is day 1
    assert f["precip_prevday_mm"].iloc[0] == pytest.approx(24.0)   # 24 h x 1 mm
    # independent check of the 24 h window with numpy's own interpolation
    series = w[w["rep"] == 0].sort_values("time")["u10"].to_numpy()
    T = 48 + 8.5
    expected = np.mean([np.interp(T - k, np.arange(len(series)), series) for k in range(24)])
    assert f["u_24h"].iloc[0] == pytest.approx(expected)


def test_each_cell_uses_its_own_pixel_and_time():
    w = _synthetic()
    obs = pd.DataFrame({"cell_id": ["a", "b"], "date": [pd.Timestamp("2024-01-03")] * 2,
                        "obs_h": [7.0, 8.0]})
    groups = pd.DataFrame({"cell_id": ["a", "b"], "rep": [0, 1]})
    f = build_features(w, obs, groups).set_index("cell_id")
    assert f.loc["a", "u_ovp"] == pytest.approx(7.0)           # pixel 0 at 07:00
    assert f.loc["b", "u_ovp"] == pytest.approx(9.0)           # pixel 1 (u + 1) at 08:00


def test_missing_observation_time_gives_nan_features():
    w = _synthetic()
    obs = pd.DataFrame({"cell_id": ["a"], "date": [pd.Timestamp("2024-01-03")], "obs_h": [np.nan]})
    groups = pd.DataFrame({"cell_id": ["a"], "rep": [0]})
    f = build_features(w, obs, groups)
    assert f[FEATURES].isna().all(axis=None)


def test_gap_in_weather_is_rejected():
    w = _synthetic().drop(index=10)
    obs = pd.DataFrame({"cell_id": ["a"], "date": [pd.Timestamp("2024-01-03")], "obs_h": [8.0]})
    groups = pd.DataFrame({"cell_id": ["a"], "rep": [0]})
    with pytest.raises(ValueError):
        build_features(w, obs, groups)

def test_trailing_mean_marks_windows_with_a_missing_value():
    a = np.arange(30.0)
    a[10] = np.nan
    m = trailing_mean(a, 5)
    assert not np.isnan(m[9])                       # window 5..9: complete
    assert np.isnan(m[10:15]).all()                 # windows ending 10..14 contain index 10
    assert not np.isnan(m[15])                      # window 11..15: complete


def test_interp_on_an_exact_hour_ignores_a_missing_next_hour():
    a = np.array([1.0, 2.0, np.nan, 4.0])
    assert interp(a, 1.0) == pytest.approx(2.0)
    assert np.isnan(interp(a, 1.5))


def test_missing_precip_hour_gives_nan_only_for_the_affected_precip_features():
    w = _synthetic()
    # day 2 (2024-01-03): previous day is 2024-01-02; blank one hour of it, pixel 0
    mask = (w["rep"] == 0) & (w["time"] == pd.Timestamp("2024-01-02 15:00"))
    w.loc[mask, "tp"] = np.nan
    obs = pd.DataFrame({"cell_id": ["a", "b"], "date": [pd.Timestamp("2024-01-03")] * 2,
                        "obs_h": [8.5, 8.5]})
    groups = pd.DataFrame({"cell_id": ["a", "b"], "rep": [0, 1]})
    f = build_features(w, obs, groups).set_index("cell_id")
    assert np.isnan(f.loc["a", "precip_prevday_mm"])            # window has the missing hour
    assert f.loc["b", "precip_prevday_mm"] == pytest.approx(24.0)   # other pixel complete
    assert f.loc["a", "u_ovp"] == pytest.approx(8.5)            # wind unaffected
    assert f.loc["a", "precip_ovp_mm"] == pytest.approx(1.0)    # bracketing hours complete


def test_missing_precip_at_a_bracketing_hour_gives_nan_precip_ovp():
    w = _synthetic()
    w.loc[(w["rep"] == 0) & (w["time"] == pd.Timestamp("2024-01-03 09:00")), "tp"] = np.nan
    obs = pd.DataFrame({"cell_id": ["a"], "date": [pd.Timestamp("2024-01-03")], "obs_h": [8.5]})
    groups = pd.DataFrame({"cell_id": ["a"], "rep": [0]})
    f = build_features(w, obs, groups)
    assert np.isnan(f["precip_ovp_mm"].iloc[0])