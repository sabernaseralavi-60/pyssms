"""Lateral margin: analytic cases and a check against the independent time-time code."""

import numpy as np
import pytest

from pyssms import indicators
from pyssms.margins import lateral_margin
from pyssms.reference import random_encounters

L, W = 4.5, 1.8


def _normals(e):
    d1 = np.stack([np.cos(e.heading1), np.sin(e.heading1)], -1)
    d2 = np.stack([np.cos(e.heading2), np.sin(e.heading2)], -1)
    return np.stack([-d1[:, 1], d1[:, 0]], -1), np.stack([-d2[:, 1], d2[:, 0]], -1)


def _margin(e, horizon=10.0):
    n1, n2 = _normals(e)
    return lateral_margin(
        e.shape1, e.pos1, e.vel1, n1, e.shape2, e.pos2, e.vel2, n2, horizon=horizon
    )


def test_overtaking_in_the_adjacent_lane_needs_lane_width_minus_body_width():
    from pyssms.reference.scenarios import Encounters

    one = lambda *x: np.array([x], float)  # noqa: E731
    e = Encounters(
        pos1=one(0.0, 0.0),
        vel1=one(10.0, 0.0),
        heading1=np.array([0.0]),
        size1=one(L, W),
        pos2=one(-30.0, 3.5),
        vel2=one(15.0, 0.0),
        heading2=np.array([0.0]),
        size2=one(L, W),
    )
    m = _margin(e)
    assert m["margin1"][0] == pytest.approx(3.5 - W)
    assert m["margin2"][0] == pytest.approx(3.5 - W)
    assert m["margin"][0] == pytest.approx(1.7)
    # without closing speed the lanes never meet: no margin within the limits
    e2 = Encounters(
        pos1=one(0.0, 0.0),
        vel1=one(10.0, 0.0),
        heading1=np.array([0.0]),
        size1=one(L, W),
        pos2=one(-30.0, 3.5),
        vel2=one(10.0, 0.0),
        heading2=np.array([0.0]),
        size2=one(L, W),
    )
    assert np.isnan(_margin(e2)["margin"][0])


def test_collision_course_has_zero_margin():
    e = random_encounters(2000, "generic", seed=31)
    k = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, horizon=10.0)
    m = _margin(e)["margin"]
    on_course = k.state == "A"
    assert on_course.sum() > 300
    np.testing.assert_allclose(m[on_course], 0.0, atol=1e-9)


def test_margin_is_the_threshold_of_a_collision_course_in_the_independent_code():
    e = random_encounters(3000, "generic", seed=32)
    n1, n2 = _normals(e)
    res = _margin(e)
    k = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, horizon=10.0)
    use = np.where((k.state != "A") & np.isfinite(res["margin"]) & (res["margin"] > 0.05))[0]
    assert len(use) > 200
    checked = 0
    for who in (1, 2):
        idx = use[np.isclose(res["margin"][use], res[f"margin{who}"][use])]
        for factor, expect_collision in ((1.002, True), (0.998, False)):
            shift = res[f"shift{who}"][idx] * factor
            p1, p2 = e.pos1[idx].copy(), e.pos2[idx].copy()
            if who == 1:
                p1 = p1 + shift[:, None] * n1[idx]
            else:
                p2 = p2 + shift[:, None] * n2[idx]
            kk = indicators(e.shape1[idx], p1, e.vel1[idx], e.shape2[idx], p2, e.vel2[idx], 10.0)
            hit = np.asarray(kk.state == "A")
            assert (hit == expect_collision).mean() > 0.99, (who, factor)
            checked += len(idx)
    assert checked > 200


def test_state_c_gets_a_finite_margin():
    e = random_encounters(3000, "generic", seed=33)
    k = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, horizon=10.0)
    m = _margin(e)["margin"]
    c = k.state == "C"
    assert c.sum() > 100
    assert np.isfinite(m[c]).mean() > 0.5
