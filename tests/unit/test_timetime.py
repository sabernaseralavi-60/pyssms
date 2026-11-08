"""Analytic cases from Laureshyn et al. (2010), Section 4 and Fig. 3, and degenerate cases."""

import numpy as np
import pytest

from pyssms import conflict_polygon, indicators, indicators_rect, rectangle
from pyssms.reference import random_encounters

L, W = 4.5, 1.8


def test_eq1_right_angle_first_user_in_the_area():
    # Fig. 3a: user 1 moves +y, user 2 moves -x; area = [-W/2, W/2]^2
    d1, v1, d2, v2 = 5.0, 10.0, 10.0, 10.0  # d1/v1 < d2/v2 < (d1+l1+w2)/v1
    k = indicators_rect(
        0,
        -W / 2 - d1 - L / 2,
        np.pi / 2,
        0,
        v1,
        L,
        W,
        W / 2 + d2 + L / 2,
        0,
        np.pi,
        -v2,
        0,
        L,
        W,
    )
    assert k.ttc[0] == pytest.approx(d2 / v2)
    assert k.state[0] == "A"


def test_eq1_right_angle_second_case():
    d1, v1, d2, v2 = 10.0, 10.0, 5.0, 10.0  # d2/v2 < d1/v1 < (d2+l2+w1)/v2
    k = indicators_rect(
        0,
        -W / 2 - d1 - L / 2,
        np.pi / 2,
        0,
        v1,
        L,
        W,
        W / 2 + d2 + L / 2,
        0,
        np.pi,
        -v2,
        0,
        L,
        W,
    )
    assert k.ttc[0] == pytest.approx(d1 / v1)


def test_eq2_rear_end_and_time_gap_below_ttc():
    x1, x2, v1, v2 = 30.0, 10.0, 5.0, 15.0  # fronts; user 2 follows faster
    k = indicators_rect(x1 - L / 2, 0, 0, v1, 0, L, W, x2 - L / 2, 0, 0, v2, 0, L, W)
    assert k.ttc[0] == pytest.approx((x1 - x2 - L) / (v2 - v1))
    # TG: the follower reaches the place where the leader's rear is now (Fig. 8)
    assert k.tg[0] == pytest.approx((x1 - L - x2) / v2)
    assert k.tg[0] < k.ttc[0]


def test_eq3_head_on():
    x1, x2, v1, v2 = 40.0, 10.0, 10.0, 5.0  # user 1 moves -x, user 2 moves +x
    k = indicators_rect(x1 + L / 2, 0, np.pi, -v1, 0, L, W, x2 - L / 2, 0, 0, v2, 0, L, W)
    assert k.ttc[0] == pytest.approx((x1 - x2) / (v1 + v2))


def test_crossing_course_time_advantage():
    # occupancy windows of the common square: user 1 [1.685, 2.315], user 2 [2.685, 3.315]
    k = indicators_rect(-20, 0, 0, 10, 0, L, W, 0, -30, np.pi / 2, 0, 10, L, W)
    assert k.state[0] == "B"
    assert np.isnan(k.ttc[0])
    assert k.tadv[0] == pytest.approx(0.37)
    assert k.t2[0] == pytest.approx(2.685)
    assert k.tg[0] == pytest.approx(2.685)
    assert k.first[0] == 1


def test_conflict_polygon_is_the_rectangle_of_occupancy_windows():
    poly = conflict_polygon(
        rectangle(0, L, W), [-20, 0], [10, 0], rectangle(np.pi / 2, L, W), [0, -30], [0, 10]
    )
    assert poly.shape == (4, 2)
    np.testing.assert_allclose(np.sort(np.unique(poly[:, 0])), [1.685, 2.315], atol=1e-9)
    np.testing.assert_allclose(np.sort(np.unique(poly[:, 1])), [2.685, 3.315], atol=1e-9)


def test_standing_road_user_is_a_collision_course():
    k = indicators_rect(0, 0, 0, 10, 0, L, W, 20 + L, 0, 0, 0, 0, L, W)
    assert k.state[0] == "A"
    assert k.ttc[0] == pytest.approx(2.0)


def test_both_standing():
    k = indicators_rect(0, 0, 0, 0, 0, L, W, 10, 0, 0, 0, 0, L, W)
    assert k.state[0] == "C"
    assert np.isnan(k.ttc[0]) and np.isnan(k.tg[0])


def test_parallel_lanes_are_state_c():
    k = indicators_rect(0, 0, 0, 10, 0, L, W, 0, 3.5, 0, 10, 0, L, W)
    assert k.state[0] == "C"
    assert np.isnan(k.tadv[0]) and np.isnan(k.tg[0])


def test_overlapping_bodies_have_zero_ttc():
    k = indicators_rect(0, 0, 0, 10, 0, L, W, 1.0, 0.5, 1.0, 3, 3, L, W)
    assert k.ttc[0] == 0.0


def test_beyond_horizon_is_nan():
    k = indicators_rect(0, 0, 0, 1, 0, L, W, 200, 0, np.pi, -1, 0, L, W, horizon=60)
    assert np.isnan(k.ttc[0])


def test_block_size_does_not_change_the_result() -> None:
    """The block size is a speed setting only: every field is identical for any block size."""
    e = random_encounters(1500, "generic", 3)
    args = (e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2)
    ref = indicators(*args, chunk=1500)
    for chunk in (7, 500, 20_000):
        out = indicators(*args, chunk=chunk)
        for f in ("ttc", "tadv", "t2", "tg"):
            assert np.array_equal(getattr(ref, f), getattr(out, f), equal_nan=True)
        assert np.array_equal(ref.first, out.first) and np.array_equal(ref.state, out.state)


@pytest.mark.parametrize("kind", ["generic", "parallel", "axis_aligned", "stopped", "overlap"])
def test_fast_form_gives_the_same_indicators(kind):
    """The 8-row form (side faces folded into the horizon box) describes the same polygon."""
    from pyssms.reference import random_encounters

    e = random_encounters(20000, kind=kind, seed=11)
    slow = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, 60.0, fast=False)
    fast = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, 60.0, fast=True)
    for f in ("ttc", "tadv", "t2", "tg"):
        a, b = getattr(slow, f), getattr(fast, f)
        np.testing.assert_array_equal(np.isnan(a), np.isnan(b), err_msg=f)
        np.testing.assert_allclose(a, b, rtol=0, atol=1e-9, equal_nan=True, err_msg=f)
    np.testing.assert_array_equal(slow.state, fast.state)
    np.testing.assert_array_equal(slow.first, fast.first)


def test_fast_form_is_used_only_where_the_side_faces_are_axis_parallel():
    from pyssms.timetime import _side_rows_axis_parallel, constraint_rows

    n = 5
    rng = np.random.default_rng(3)
    h = rng.uniform(-np.pi, np.pi, n)
    sh = rectangle(h, 4.5, 1.8)
    v_aligned = 10.0 * np.stack([np.cos(h), np.sin(h)], -1)
    v_skew = 10.0 * np.stack([np.cos(h + 0.2), np.sin(h + 0.2)], -1)
    pos1, pos2 = np.zeros((n, 2)), np.array([[30.0, 5.0]] * n)
    a, c, _, _ = constraint_rows(sh, pos1, v_aligned, sh, pos2, v_aligned, 60.0)
    assert _side_rows_axis_parallel(a, c).all()
    a, c, _, _ = constraint_rows(sh, pos1, v_skew, sh, pos2, v_aligned, 60.0)
    assert not _side_rows_axis_parallel(a, c).any()  # body 1 does not move along its length
