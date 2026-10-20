from no2.solar import observation_utc_hours, hhmm


def test_matches_measured_january_overpass():
    # 2024-01-15 over Delhi: zenith 51.0, azimuth -166.1 -> script 07 gave 07:45 UTC
    t = observation_utc_hours(15, 51.0, -166.1, 77.2, 28.6)
    assert abs(t - 7.75) < 0.05


def test_morning_sun_gives_earlier_time():
    afternoon = observation_utc_hours(15, 51.0, -166.1, 77.2, 28.6)
    morning = observation_utc_hours(15, 51.0, 166.1, 77.2, 28.6)
    assert morning < afternoon


def test_hhmm_formatting():
    assert hhmm(7.75) == "07:45"
    assert hhmm(7.999) == "08:00"