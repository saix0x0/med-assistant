from app.core import medicines as m


def test_exact_match():
    r = m.match("Dolo 650")
    assert r.matched and r.name == "Dolo 650"
    assert r.ingredient == "Paracetamol"


def test_ocr_noise_recovers():
    # "Doio 65O" -> Dolo 650
    r = m.match("Doio 65O")
    assert r.matched and r.name == "Dolo 650"


def test_refuses_unknown():
    r = m.match("Zxqwplid")
    assert not r.matched and r.name is None


def test_strength_ignored_in_name():
    r = m.match("azithral 500 mg")
    assert r.matched and "Azithral" in r.name
