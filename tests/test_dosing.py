from app.core.dosing import parse_dose


def test_numeric_three_slot():
    d = parse_dose("1-0-1 a/f x5d")
    assert (d.morning, d.noon, d.night) == (1, 0, 1)
    assert d.food == "after"
    assert d.days == 5


def test_numeric_four_slot():
    d = parse_dose("1-0-0-1")
    assert (d.morning, d.noon, d.evening, d.night) == (1, 0, 0, 1)


def test_bd_tds_od():
    assert parse_dose("BD").total_per_day == 2
    assert parse_dose("TDS").total_per_day == 3
    assert parse_dose("OD").total_per_day == 1


def test_before_food_and_days():
    d = parse_dose("1-0-0 b/f for 7 days")
    assert d.food == "before"
    assert d.days == 7


def test_sos_prn():
    assert parse_dose("SOS").prn is True


def test_ocr_noisy_separator():
    d = parse_dose("1 - 0 - 1")
    assert (d.morning, d.night) == (1, 1)
