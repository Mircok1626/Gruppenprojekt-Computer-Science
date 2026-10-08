import pytest

from core import dosage


def test_product_per_ha_folpet():
    assert dosage.product_per_ha(0.125, 1200) == pytest.approx(1.5)


def test_per_parcel_and_water():
    assert dosage.per_parcel(1.5, 0.8) == pytest.approx(1.2)
    assert dosage.water_per_parcel(300, 0.8) == pytest.approx(240)


def test_per_tank():
    assert dosage.per_tank(1.5, 300, 200) == pytest.approx(1.0)


def test_tank_fillings():
    assert dosage.tank_fillings(240, 200) == 2


def test_invalid_water():
    with pytest.raises(ValueError):
        dosage.per_tank(1.5, 0, 200)
