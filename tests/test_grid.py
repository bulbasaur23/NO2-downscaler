from no2.grid import cell_index, cell_bounds, cells_in_bbox, make_cell_id

def test_point_maps_to_cell_containing_it():
    ix, iy = cell_index(77.23, 28.61)          # central Delhi
    w, s, e, n = cell_bounds(ix, iy)
    assert w <= 77.23 < e and s <= 28.61 < n

def test_edge_point_is_stable():
    # a point exactly on a cell edge must land in the cell to its east/north
    ix, iy = cell_index(77.80, 28.20)
    assert cell_bounds(ix, iy)[0] == 77.80
    assert cell_bounds(ix, iy)[1] == 28.20

def test_bbox_cell_count():
    df = cells_in_bbox(76.80, 28.20, 77.80, 29.00)
    assert len(df) == 20 * 16                  # 1.0 deg / 0.05 x 0.8 deg / 0.05
    assert df["cell_id"].is_unique

def test_id_roundtrip():
    assert make_cell_id(5000, 2000) == "2000_5000"