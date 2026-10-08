"""Formel 5: Mittel- und Wassermenge pro Hektar, Parzelle und Tankfüllung.

Hinweis aus dem Projektplan: Dieses Modul eignet sich gut, um es bewusst ohne
KI zu schreiben (Prüfungsvorbereitung). Der Code hier ist nur ein Vorschlag.
"""
from __future__ import annotations

import math


def product_per_ha(conc_pct: float, base_broth_l_ha: float) -> float:
    """Mittelmenge pro ha = Konzentration (%) × Basisbrühmenge des Stadiums.

    Beispiel: Folpet 0,125 % × 1200 l/ha -> 1,5 kg/ha.
    """
    return conc_pct / 100.0 * base_broth_l_ha


def per_parcel(amount_per_ha: float, area_ha: float) -> float:
    """Menge für die ganze Parzelle. Beispiel: 1,5 kg/ha × 0,8 ha -> 1,2 kg."""
    return amount_per_ha * area_ha


def water_per_parcel(water_l_ha: float, area_ha: float) -> float:
    """Wassermenge für die Parzelle. Beispiel: 300 l/ha × 0,8 ha -> 240 l."""
    return water_l_ha * area_ha


def per_tank(amount_per_ha: float, water_l_ha: float, tank_l: float) -> float:
    """Mittelmenge pro (voller) Tankfüllung.

    Das Gerät bringt ``water_l_ha`` aus; ein Tank reicht für tank_l / water_l_ha ha.
    Beispiel: 1,5 kg/ha, 300 l/ha, 200-l-Tank -> 1,0 kg.
    """
    if water_l_ha <= 0:
        raise ValueError("Wassermenge pro ha muss grösser als 0 sein.")
    return amount_per_ha * tank_l / water_l_ha


def tank_fillings(water_total_l: float, tank_l: float) -> int:
    """Anzahl (angebrochener) Tankfüllungen."""
    if tank_l <= 0:
        raise ValueError("Tankgrösse muss grösser als 0 sein.")
    return math.ceil(water_total_l / tank_l)


def concentration_factor(base_broth_l_ha: float, water_l_ha: float) -> float:
    """Konzentrierungsfaktor des Sprühgeräts gegenüber der Basisbrühe."""
    return base_broth_l_ha / water_l_ha if water_l_ha else float("nan")
