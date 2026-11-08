"""Delta-V and Extended Delta-V against the printed Table 1 of Laureshyn et al. (2017)."""

from importlib import resources

import numpy as np
import pytest
import yaml

from pyssms.severity import MASS_RATIO_TO_CAR, delta_v, extended_delta_v, reduced_velocity


def _rows():
    text = (
        resources.files("pyssms.validation")
        .joinpath("data/laureshyn2017_table1.yaml")
        .read_text(encoding="utf-8")
    )
    return yaml.safe_load(text)["rows"]


def test_table1_has_twenty_rows():
    assert len(_rows()) == 20


#: Rows of Table 1 (1-based) whose printed Delta-V0 is not reproduced by the paper's own formula
#: from the printed relative speed and mass ratio, beyond the rounding of the printed numbers.
#: Row 5: printed 6.9, formula 7.05. Row 9 (car-HGV): printed 15.2, formula 13.65 (a mass ratio of
#: about 7.6 would be needed, not 3.85). Unexplained; possible typos or a different time instant;
#: recorded, never tuned away.
KNOWN_GAPS = {5, 9}


def _computed_dv0(r):
    rel = np.array([[r["vrel"], 0.0]])
    dv_light, dv_heavy = delta_v(1.0, r["mass_ratio"], rel, np.zeros((1, 2)))
    return max(dv_light[0], dv_heavy[0])


def test_delta_v0_reproduces_printed_table_except_the_documented_gaps():
    outside = set()
    for i, r in enumerate(_rows(), 1):
        mu = r["mass_ratio"] / (r["mass_ratio"] + 1.0)
        slack = mu * 0.05 + 0.05  # rounding of the printed relative speed and of the printed dv0
        if abs(_computed_dv0(r) - r["dv0"]) > slack:
            outside.add(i)
    assert outside == KNOWN_GAPS


def test_documented_gap_sizes():
    rows = _rows()
    assert _computed_dv0(rows[4]) - rows[4]["dv0"] == pytest.approx(0.15, abs=0.01)
    assert _computed_dv0(rows[8]) - rows[8]["dv0"] == pytest.approx(-1.55, abs=0.01)


def test_extended_delta_v_obeys_the_triangle_bound_for_every_row():
    # braking both road users for T2 changes the relative velocity by at most 2 a T2, so
    # |dv_a - dv_0| <= mu * 2 a T2 with mu = heavy / (heavy + light)  (necessary condition only)
    for r in _rows():
        mu = r["mass_ratio"] / (r["mass_ratio"] + 1.0)
        for a, key in ((4.0, "dv4"), (8.0, "dv8")):
            bound = mu * 2 * a * r["t2min"] + 0.1
            assert abs(r[key] - r["dv0"]) <= bound, (a, r)


def test_headon_equal_cars_braking_and_floor():
    v1, v2 = np.array([[10.0, 0.0]]), np.array([[-10.0, 0.0]])
    assert extended_delta_v(1, 1, v1, v2, 0.0, 4.0)[2][0] == pytest.approx(10.0)
    assert extended_delta_v(1, 1, v1, v2, 1.0, 4.0)[2][0] == pytest.approx(6.0)
    assert extended_delta_v(1, 1, v1, v2, 3.0, 4.0)[2][0] == 0.0  # both stopped


def test_lighter_road_user_has_the_larger_delta_v():
    car, hgv = 1.0, MASS_RATIO_TO_CAR["hgv"]
    dv_car, dv_hgv, severity = extended_delta_v(car, hgv, [[10.0, 0.0]], [[0.0, 10.0]], 0.0, 0.0)
    assert dv_car[0] > dv_hgv[0]
    assert severity[0] == dv_car[0]
    assert dv_car[0] == pytest.approx(hgv / (hgv + car) * np.hypot(10, 10))


def test_reduced_velocity_keeps_direction_and_rest():
    out = reduced_velocity([[3.0, 4.0], [0.0, 0.0]], 1.0, 2.0)
    np.testing.assert_allclose(out[0], [3.0 * 3.0 / 5.0, 4.0 * 3.0 / 5.0])
    np.testing.assert_allclose(out[1], [0.0, 0.0])
