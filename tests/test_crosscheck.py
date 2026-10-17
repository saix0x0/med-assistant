from datetime import date

from app.core import crosscheck as cc
from app.core import prescription as rx_mod

TODAY = date(2026, 10, 17)
RX = rx_mod.parse(
    "Tab. Dolo 650 1-0-1 x5d a/f\n"
    "Cap. Azithral 500 0-0-1 x3d\n"
    "Tab. Pan-D 40 1-0-0 x5d b/f\n")


def test_on_list():
    r = cc.check("Dolo 650", "650 mg", "03/2027", RX, today=TODAY)
    assert r.verdict == cc.ON_LIST
    assert r.matched_medicine is not None


def test_not_on_list():
    r = cc.check("Shelcal 500", "500 mg", "12/2027", RX, today=TODAY)
    assert r.verdict == cc.NOT_ON_LIST


def test_expired():
    r = cc.check("Azithral 500", "500 mg", "06/2026", RX, today=TODAY)
    assert r.verdict == cc.EXPIRED
    assert r.expired is True


def test_unreadable():
    r = cc.check("", "", "", RX, today=TODAY)
    assert r.verdict == cc.UNREADABLE


def test_expiry_mmm_yyyy():
    r = cc.check("Dolo 650", "650 mg", "MAR 2025", RX, today=TODAY)
    assert r.verdict == cc.EXPIRED
