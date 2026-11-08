"""Invariance of the indicators and margins under changes that cannot matter physically."""

import numpy as np
import pytest

from pyssms import indicators
from pyssms.disturbance import disturbance_set
from pyssms.margins import lateral_margin
from pyssms.reference import random_encounters

T = 10.0
N = 3000


def _rot(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]])


def _ind(shape1, pos1, vel1, shape2, pos2, vel2, horizon=T):
    return indicators(shape1, pos1, vel1, shape2, pos2, vel2, horizon=horizon)


def _same(x, y, atol=1e-7):
    assert ((np.isnan(x) & np.isnan(y)) | (np.abs(x - y) <= atol)).all()


def _fields(k):
    return {f: getattr(k, f) for f in ("ttc", "tadv", "t2", "tg")}


@pytest.fixture(scope="module")
def enc():
    return random_encounters(N, "generic", seed=51)


def test_indicators_do_not_depend_on_the_coordinate_system(enc):
    base = _ind(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2)
    rot, shift = _rot(0.83), np.array([123.0, -57.0])
    moved = _ind(
        enc.shape1 @ rot.T,
        enc.pos1 @ rot.T + shift,
        enc.vel1 @ rot.T,
        enc.shape2 @ rot.T,
        enc.pos2 @ rot.T + shift,
        enc.vel2 @ rot.T,
    )
    for name, v in _fields(base).items():
        _same(v, _fields(moved)[name])
    assert (base.state == moved.state).all()
    assert (base.first == moved.first).all()


def test_swapping_the_road_users_swaps_only_who_passes_first(enc):
    a = _ind(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2)
    b = _ind(enc.shape2, enc.pos2, enc.vel2, enc.shape1, enc.pos1, enc.vel1)
    for name, v in _fields(a).items():
        _same(v, _fields(b)[name])
    assert (a.state == b.state).all()
    passed = a.first > 0
    assert passed.sum() > 500
    assert (a.first[passed] == 3 - b.first[passed]).all()


def test_scaling_lengths_leaves_times_unchanged(enc):
    s = 2.5
    a = _ind(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2)
    b = _ind(s * enc.shape1, s * enc.pos1, s * enc.vel1, s * enc.shape2, s * enc.pos2, s * enc.vel2)
    for name, v in _fields(a).items():
        _same(v, _fields(b)[name])


def test_scaling_speeds_scales_times_inversely(enc):
    s = 2.0
    a = _ind(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2, horizon=T)
    b = _ind(enc.shape1, enc.pos1, s * enc.vel1, enc.shape2, enc.pos2, s * enc.vel2, horizon=T / s)
    for name, v in _fields(a).items():
        _same(v / s, _fields(b)[name], atol=1e-6)
    assert (a.state == b.state).all()


def test_vertex_order_of_the_footprints_is_irrelevant(enc):
    a = _ind(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2)
    b = _ind(
        np.roll(enc.shape1, 2, axis=1),
        enc.pos1,
        enc.vel1,
        np.roll(enc.shape2, 1, axis=1),
        enc.pos2,
        enc.vel2,
    )
    for name, v in _fields(a).items():
        _same(v, _fields(b)[name])


def _normal(heading):
    return np.stack([-np.sin(heading), np.cos(heading)], -1)


def _d(shape1, pos1, vel1, shape2, pos2, vel2, normal2):
    return disturbance_set(shape1, pos1, vel1, shape2, pos2, vel2, normal2, T)


def test_disturbance_margins_do_not_depend_on_the_coordinate_system(enc):
    n2 = _normal(enc.heading2)
    base = _d(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2, n2)
    rot, shift = _rot(-1.9), np.array([-40.0, 8.0])
    moved = _d(
        enc.shape1 @ rot.T,
        enc.pos1 @ rot.T + shift,
        enc.vel1 @ rot.T,
        enc.shape2 @ rot.T,
        enc.pos2 @ rot.T + shift,
        enc.vel2 @ rot.T,
        n2 @ rot.T,
    )
    for f in ("time_margin", "lateral_margin"):
        _same(getattr(base, f)(), getattr(moved, f)(), atol=1e-6)
    _same(base.signed_margin(0.7, 1.3), moved.signed_margin(0.7, 1.3), atol=1e-6)


def test_swapping_road_users_reflects_d_through_the_origin(enc):
    # shifting road user 1 along u is shifting road user 2 along -u, and delta changes sign
    n2 = _normal(enc.heading2)
    a = _d(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2, n2)
    b = _d(enc.shape2, enc.pos2, enc.vel2, enc.shape1, enc.pos1, enc.vel1, n2)
    _same(a.time_margin(), b.time_margin(), atol=1e-6)
    _same(a.lateral_margin(), b.lateral_margin(), atol=1e-6)
    _same(a.signed_margin(0.5, 2.0), b.signed_margin(0.5, 2.0), atol=1e-6)
    rng = np.random.default_rng(3)
    delta, eps = rng.uniform(-3, 3, N), rng.uniform(-5, 5, N)
    m = a.contains(delta, eps, tol=0.0)
    mb = b.contains(-delta, -eps, tol=0.0)
    clear = ~(a.contains(delta, eps, tol=0.02) ^ a.contains(delta, eps, tol=-0.02))
    assert (m[clear] == mb[clear]).all()


def test_scaling_lengths_scales_the_lateral_margin_and_beta(enc):
    s = 3.0
    n2 = _normal(enc.heading2)
    a = _d(enc.shape1, enc.pos1, enc.vel1, enc.shape2, enc.pos2, enc.vel2, n2)
    b = _d(
        s * enc.shape1, s * enc.pos1, s * enc.vel1, s * enc.shape2, s * enc.pos2, s * enc.vel2, n2
    )
    _same(a.time_margin(), b.time_margin(), atol=1e-6)
    la, lb = a.lateral_margin(), b.lateral_margin()
    assert ((np.isnan(la) & np.isnan(lb)) | (np.abs(s * la - lb) < 1e-5)).all()
    # beta with sigma_eps scaled by s as well is unchanged
    _same(a.signed_margin(1.0, 1.0), b.signed_margin(1.0, s), atol=1e-6)


def test_margin_polygon_in_time_and_shift_agrees_after_rotation(enc):
    n1, n2 = _normal(enc.heading1), _normal(enc.heading2)
    rot = _rot(0.4)
    a = lateral_margin(enc.shape1, enc.pos1, enc.vel1, n1, enc.shape2, enc.pos2, enc.vel2, n2)
    b = lateral_margin(
        enc.shape1 @ rot.T,
        enc.pos1 @ rot.T,
        enc.vel1 @ rot.T,
        n1 @ rot.T,
        enc.shape2 @ rot.T,
        enc.pos2 @ rot.T,
        enc.vel2 @ rot.T,
        n2 @ rot.T,
    )
    _same(a["margin"], b["margin"], atol=1e-6)
