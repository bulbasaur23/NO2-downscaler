from no2.versions import parse_processor_version, normalize_processor_version

def test_leading_zeros_are_normalised():
    assert normalize_processor_version("02.09.01") == "2.9.1"

def test_plain_version_is_unchanged():
    assert normalize_processor_version("2.8.0") == "2.8.0"

def test_development_label_is_rejected():
    assert parse_processor_version("03.00.DV") is None

def test_numeric_ordering_not_text_ordering():
    assert parse_processor_version("02.09.01") > parse_processor_version("2.8.0")
    assert "02.09.01" < "2.8.0"      # the trap: as text, the newer version sorts first