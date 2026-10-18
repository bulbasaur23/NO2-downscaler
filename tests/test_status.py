from no2.status import day_status

def test_normal_day():
    assert day_status(15, 0.92, 0.0104) == "observed"      # 2024-01-15

def test_cloudy_day():
    assert day_status(14, 0.00, 0.7808) == "insufficient"  # 2024-01-04

def test_no_data_day():
    assert day_status(14, 0.00, None) == "no_overpass"     # 2024-01-28

def test_no_images():
    assert day_status(0, None, None) == "no_overpass"

def test_partial_day_boundary():
    assert day_status(14, 0.46, 0.267) == "insufficient"   # 2024-01-13