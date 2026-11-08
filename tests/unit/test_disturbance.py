"""Disturbance set D and the signed margin: analytic cases, brute force and the other modules."""

import numpy as np
import pytest

from pyssms import indicators, rectangle
from pyssms.disturbance import disturbance_set, form_probability
from pyssms.margins import lateral_margin
from pyssms.reference import random_encounters
from pyssms.reference.scenarios import Encounters

L, W = 4.5, 1.8
T = 10.0


def _left_normal(heading):
    return np.stack([-np.sin(heading), np.cos(heading)], -1)


def _dset(e, horizon=T):
    return disturbance_set(
        e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, _left_normal(e.heading2), horizon
    )


def _one(pos1, vel1, pos2, vel2, h1=0.0, h2=0.0, size1=(L, W), size2=(L, W)):
    a = lambda *x: np.array([x], float)  # noqa: E731
    return Encounters(
        pos1=a(*pos1),
        vel1=a(*vel1),
        heading1=np.array([h1]),
        size1=a(*size1),
        pos2=a(*pos2),
        vel2=a(*vel2),
        heading2=np.array([h2]),
        size2=a(*size2),
    )


def _overlap(poly_a, poly_b):
    """Separating-axis test for convex polygons, vectorised over a leading axis."""
    sep = np.zeros(poly_a.shape[0], bool)
    for poly in (poly_a, poly_b):
        edge = np.roll(poly, -1, axis=1) - poly
        nrm = np.stack([edge[..., 1], -edge[..., 0]], -1)
        for k in range(nrm.shape[1]):
            pa = np.einsum("nvd,nd->nv", poly_a, nrm[:, k])
            pb = np.einsum("nvd,nd->nv", poly_b, nrm[:, k])
            sep |= (pa.max(1) < pb.min(1) - 1e-12) | (pb.max(1) < pa.min(1) - 1e-12)
    return ~sep


def _brute_force_member(e, i, delta, eps, step=0.02):
    """Does the disturbed encounter overlap at some time? Scan, independent of the elimination."""
    t = np.arange(max(0.0, -delta), min(T, T - delta) + 1e-9, step)
    if len(t) == 0:
        return False
    u = _left_normal(e.heading2)[i]
    c1 = e.pos1[i] + e.vel1[i] * (t + delta)[:, None]
    c2 = e.pos2[i] + eps * u + e.vel2[i] * t[:, None]
    s1 = np.repeat(e.shape1[i : i + 1], len(t), axis=0)
    s2 = np.repeat(e.shape2[i : i + 1], len(t), axis=0)
    return bool(_overlap(s1 + c1[:, None, :], s2 + c2[:, None, :]).any())


def test_overtaking_in_the_adjacent_lane_has_beta_equal_to_the_lateral_gap():
    # same scenario as test_margins: road user 2 must move 3.5 - 1.8 = 1.7 m sideways
    e = _one((0.0, 0.0), (10.0, 0.0), (-30.0, 3.5), (15.0, 0.0))
    d = _dset(e)
    assert np.isnan(d.time_margin()[0])  # parallel paths: delaying never creates a collision course
    assert d.lateral_margin()[0] == pytest.approx(1.7)
    assert d.signed_margin()[0] == pytest.approx(1.7)
    assert d.signed_margin(1.0, 0.5)[0] == pytest.approx(3.4)  # eps / sigma_eps
    assert not d.contains(np.array([0.0]), np.array([0.0]))[0]
    assert d.contains(np.array([0.0]), np.array([-2.0]))[0]


def test_head_on_collision_course_has_negative_beta_and_zero_margins():
    e = _one((0.0, 0.0), (10.0, 0.0), (60.0, 0.0), (-10.0, 0.0), 0.0, np.pi)
    d = _dset(e)
    assert d.signed_margin()[0] < 0
    assert d.time_margin()[0] == 0.0 and d.lateral_margin()[0] == 0.0
    assert d.contains(np.array([0.0]), np.array([0.0]))[0]


def test_origin_in_d_iff_state_a_and_time_margin_is_tadv():
    e = random_encounters(4000, "generic", seed=41)
    k = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, horizon=T)
    d = _dset(e)
    zero = np.zeros(len(k.state))
    inside = d.contains(zero, zero)
    assert (inside == (k.state == "A")).mean() > 0.999
    tm = d.time_margin()
    use = np.isfinite(k.tadv) & (k.state != "A")
    assert use.sum() > 500
    # the horizon box can cut D differently from K only at the edge, where K reports NaN
    np.testing.assert_allclose(tm[use], k.tadv[use], atol=1e-6)
    assert np.isnan(tm[k.state == "C"]).mean() > 0.9


def test_lateral_margin_agrees_with_the_independent_time_shift_polygon():
    e = random_encounters(3000, "generic", seed=42)
    n2 = _left_normal(e.heading2)
    n1 = _left_normal(e.heading1)
    ref = lateral_margin(
        e.shape1, e.pos1, e.vel1, n1, e.shape2, e.pos2, e.vel2, n2, horizon=T, max_shift=1e6
    )["margin2"]
    lat = _dset(e).lateral_margin()
    use = np.isfinite(ref) & np.isfinite(lat)
    assert use.sum() > 1000
    np.testing.assert_allclose(lat[use], ref[use], atol=1e-6)


def test_membership_agrees_with_a_brute_force_scan():
    e = random_encounters(300, "generic", seed=43)
    d = _dset(e)
    rng = np.random.default_rng(7)
    delta = rng.uniform(-4, 4, len(d.empty))
    eps = rng.uniform(-6, 6, len(d.empty))
    member = d.contains(delta, eps, tol=0.0)
    # keep only points clearly away from the boundary (distance 0.05 in the scaled plane)
    inner = d.contains(delta, eps, tol=-0.05)
    outer = d.contains(delta, eps, tol=0.05)
    clear = inner | ~outer
    assert clear.sum() > 200
    truth = np.array([_brute_force_member(e, i, delta[i], eps[i]) for i in range(len(delta))])
    assert (truth[clear] == member[clear]).mean() > 0.99


def test_beta_is_continuous_through_the_states():
    # pedestrian crosses the path of a car; moving the pedestrian's start along its own path by
    # dy only shifts D by dy / v along the delta axis, so beta (a distance) changes by at most that
    v2 = 1.5
    ys = np.arange(-9.0, 9.0, 0.01)
    n = len(ys)
    sh1 = np.repeat(rectangle(0.0, L, W), n, axis=0)
    sh2 = np.repeat(rectangle(np.pi / 2, 0.6, 0.6), n, axis=0)
    d = disturbance_set(
        sh1,
        np.tile([0.0, 0.0], (n, 1)),
        np.tile([10.0, 0.0], (n, 1)),
        sh2,
        np.stack([np.full(n, 30.0), ys], -1),
        np.tile([0.0, v2], (n, 1)),
        np.tile([-1.0, 0.0], (n, 1)),
        horizon=T,
    )
    beta = d.signed_margin()
    k = indicators(
        sh1,
        np.zeros((n, 2)),
        np.tile([10.0, 0.0], (n, 1)),
        sh2,
        np.stack([np.full(n, 30.0), ys], -1),
        np.tile([0.0, v2], (n, 1)),
        horizon=T,
    )
    assert {"A", "B"} <= set(k.state)
    # once the pedestrian has passed the road and walks away, no disturbance of this family can
    # create a collision course: D is empty and beta is undefined (NaN), as TAdv is in state C
    ok = np.isfinite(beta)
    assert ok[k.state == "A"].all() and ok[k.state == "B"].all()
    assert (beta[k.state == "A"] <= 0).all() and (beta[k.state == "B"] >= 0).all()
    pair = ok[1:] & ok[:-1]
    assert pair.sum() > 600
    assert np.abs(np.diff(beta))[pair].max() <= 0.01 / v2 + 1e-6


def test_form_probability_is_the_gaussian_tail():
    assert form_probability(np.array([0.0]))[0] == pytest.approx(0.5)
    assert form_probability(np.array([1.0]))[0] == pytest.approx(0.158655254)
    assert np.isnan(form_probability(np.array([np.nan]))[0])


def test_form_probability_against_monte_carlo_for_a_half_plane_like_set():
    # overtaking in the adjacent lane: D is a band in eps, wide in delta, so the nearest boundary
    # dominates; disturbances: eps ~ N(0, 1.0) m, delta ~ N(0, 0.5) s
    e = _one((0.0, 0.0), (10.0, 0.0), (-30.0, 3.5), (15.0, 0.0))
    d = _dset(e)
    sd, se = 0.5, 1.0
    beta = d.signed_margin(sd, se)[0]
    rng = np.random.default_rng(11)
    m = 100_000
    from pyssms.disturbance import DisturbanceSet

    big = DisturbanceSet(np.repeat(d.g, m, 0), np.repeat(d.h, m, 0), np.repeat(d.empty, m, 0))
    hit = big.contains(rng.normal(0, sd, m), rng.normal(0, se, m)).mean()
    # one-sided approximation: the far side of the band (eps < -5.3) is also "collision"
    assert hit == pytest.approx(form_probability(np.array([beta]))[0], abs=0.01)
