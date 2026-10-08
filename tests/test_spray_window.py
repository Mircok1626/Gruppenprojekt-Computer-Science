from core import spray_window

THURSDAY = "2026-05-07"
SUNDAY = "2026-05-10"


def _day(date=THURSDAY, rain=0.0, rain6=None, wind=5.0, tmax=22.0):
    return {"date": date, "rain_mm": rain, "rain_6h_min": rain6, "wind_mean": wind, "t_max": tmax}


def test_good_day_is_green():
    status, reasons = spray_window.day_status(_day())
    assert status == "grün"
    assert reasons == ["gute Bedingungen"]


def test_sunday_is_red():
    assert spray_window.day_status(_day(date=SUNDAY))[0] == "rot"


def test_rain_after_spraying_is_red():
    assert spray_window.day_status(_day(rain=5.0, rain6=1.5))[0] == "rot"


def test_rain_window_dry_is_green():
    # viel Regen am Abend, aber trockenes 6-h-Fenster am Morgen
    assert spray_window.day_status(_day(rain=8.0, rain6=0.0))[0] == "grün"


def test_wind_yellow():
    assert spray_window.day_status(_day(wind=17))[0] == "gelb"


def test_heat_only_for_sensitive_products():
    assert spray_window.day_status(_day(tmax=32))[0] == "grün"
    assert spray_window.day_status(_day(tmax=32), heat_sensitive=True)[0] == "rot"
