from datetime import date

from core import protection


def test_is_protected_examples():
    assert protection.is_protected(date(2026, 5, 11), date(2026, 5, 5))
    assert not protection.is_protected(date(2026, 5, 16), date(2026, 5, 5))
    assert not protection.is_protected(date(2026, 5, 11), None)


def test_protected_until():
    assert protection.protected_until(date(2026, 5, 5)) == date(2026, 5, 15)


def test_infection_status():
    sprays = [date(2026, 5, 5)]
    today = date(2026, 5, 20)
    assert protection.infection_status(date(2026, 5, 11), date(2026, 5, 18), sprays, today) == "geschützt"
    assert protection.infection_status(date(2026, 5, 16), date(2026, 5, 25), sprays, today) == "offen"
    assert protection.infection_status(date(2026, 5, 16), date(2026, 5, 19), sprays, today) == "verpasst"
    assert protection.infection_status(date(2026, 5, 16), date(2026, 5, 25),
                                       sprays + [date(2026, 5, 18)], today) == "behandelt"
