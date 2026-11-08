"""Injury risk curves of Lubbe, Wu and Jeppsson (2022), coefficients of their Tables 2-5."""

import numpy as np
import pytest

from pyssms.severity import (
    INJURY_COEFFICIENTS,
    extended_closing_speed,
    injury_risk,
    safe_closing_speed,
)


@pytest.mark.parametrize(
    ("user", "age", "printed_kmh"),
    # "A 10% MAIS3+F injury risk corresponds to a closing speed of 29 km/h for pedestrians, 44 km/h
    # for cyclists, 48 km/h for motorcyclists and 112 km/h for car drivers" (abstract, Section 5),
    # at the median ages of the samples (46, 39, 37, 39 years, Section 4).
    [
        ("pedestrian", 46, 29),
        ("cyclist", 39, 44),
        ("motorcyclist", 37, 48),
        ("car_driver", 39, 112),
    ],
)
def test_safe_speeds_of_the_paper_follow_from_the_printed_coefficients(user, age, printed_kmh):
    # the coefficients are printed to three decimals, which limits the match to about 1.5 km/h
    v = safe_closing_speed(user, "MAIS3+F", age, 0.10)
    assert v == pytest.approx(printed_kmh, abs=1.5)
    assert injury_risk(user, "MAIS3+F", v, age) == pytest.approx(0.10)


def test_risk_curves_are_ordered_and_increase_with_speed_and_age():
    # the three levels are fitted separately: for cyclists the curves cross above about 90 km/h
    # (age 65), outside the range of the data, so the ordering is only tested up to 80 km/h
    v = np.linspace(10, 80, 50)
    assert len(INJURY_COEFFICIENTS) == 12
    for user in ("pedestrian", "cyclist", "motorcyclist", "car_driver"):
        r2 = injury_risk(user, "MAIS2+F", v, 65)
        r3 = injury_risk(user, "MAIS3+F", v, 65)
        rf = injury_risk(user, "fatal", v, 65)
        assert (r2 >= r3).all()
        assert (r3 >= rf).all()
        assert (np.diff(r3) > 0).all()
        assert (injury_risk(user, "MAIS3+F", v, 80) > injury_risk(user, "MAIS3+F", v, 30)).all()


def test_pedestrians_are_more_vulnerable_than_car_drivers_at_every_speed_and_level():
    v = np.linspace(20, 90, 30)
    for level in ("MAIS2+F", "MAIS3+F", "fatal"):
        ped = injury_risk("pedestrian", level, v, 46)
        car = injury_risk("car_driver", level, v, 46)
        assert (ped > car).all()


def test_extended_closing_speed_in_kmh_and_braking():
    v1, v2 = np.array([[10.0, 0.0]]), np.array([[0.0, 0.0]])
    assert extended_closing_speed(v1, v2, 0.0)[0] == pytest.approx(36.0)
    assert extended_closing_speed(v1, v2, 1.0, decel=4.0)[0] == pytest.approx(3.6 * 6.0)
    assert extended_closing_speed(v1, v2, 5.0, decel=4.0)[0] == pytest.approx(0.0)
