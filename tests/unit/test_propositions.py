"""Numerical checks of the propositions of Appendix A of the methods paper."""

import numpy as np

from pyssms import indicators
from pyssms.disturbance import DisturbanceSet, disturbance_set, form_probability
from pyssms.reference import random_encounters

T = 10.0


def _left(h):
    return np.stack([-np.sin(h), np.cos(h)], -1)


def _dset(e, normal):
    return disturbance_set(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, normal, T)


def _support_beta(d, i, scale):
    """beta = -min over unit u of the support function of the scaled set (kink refined)."""
    v = d.vertices(i) / scale
    ang = np.linspace(0.0, 2 * np.pi, 3600, endpoint=False)
    u = np.stack([np.cos(ang), np.sin(ang)], -1)
    h = (u @ v.T).max(axis=1)
    k = int(np.argmin(h))
    lo, hi = ang[k] - 2 * (ang[1] - ang[0]), ang[k] + 2 * (ang[1] - ang[0])
    for _ in range(60):
        a, b = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        fa = (np.array([np.cos(a), np.sin(a)]) @ v.T).max()
        fb = (np.array([np.cos(b), np.sin(b)]) @ v.T).max()
        if fa < fb:
            hi = b
        else:
            lo = a
    m = 0.5 * (lo + hi)
    return -min(h.min(), (np.array([np.cos(m), np.sin(m)]) @ v.T).max())


def test_signed_margin_is_minus_the_smallest_support_value_of_the_scaled_set():
    e = random_encounters(80, "generic", seed=72)
    d = _dset(e, _left(e.heading2))
    scale = np.array([0.7, 1.3])
    beta = d.signed_margin(*scale)
    checked = 0
    for i in range(len(beta)):
        if np.isfinite(beta[i]):
            assert abs(_support_beta(d, i, scale) - beta[i]) < 1e-5
            checked += 1
    assert checked > 40


def test_phi_of_minus_beta_bounds_the_collision_course_probability():
    # outside D: P <= Phi(-beta) (D lies in the half-plane beyond the nearest point);
    # inside D: P >= 1 - exp(-beta^2 / 2) (D contains the disc of radius |beta|)
    e = random_encounters(60, "generic", seed=73)
    d = _dset(e, _left(e.heading2))
    sd, se = 0.7, 1.3
    beta = d.signed_margin(sd, se)
    rng = np.random.default_rng(1)
    m = 8000
    outside = inside = 0
    for i in range(len(beta)):
        if not np.isfinite(beta[i]):
            continue
        dd = DisturbanceSet(
            np.repeat(d.g[i : i + 1], m, 0),
            np.repeat(d.h[i : i + 1], m, 0),
            np.repeat(d.empty[i : i + 1], m, 0),
        )
        x = rng.normal(0, 1, (m, 2)) * np.array([sd, se])
        p = float(dd.contains(x[:, 0], x[:, 1]).mean())
        err = 4 * (max(p * (1 - p), 1e-4) / m) ** 0.5
        if beta[i] > 0:
            outside += 1
            assert p <= float(form_probability(np.array([beta[i]]))[0]) + err
        else:
            inside += 1
            assert p >= 1.0 - np.exp(-0.5 * beta[i] ** 2) - err
    assert outside > 10 and inside > 5


def test_lateral_margin_along_the_velocity_of_road_user_1_is_speed_times_time_advantage():
    # a shift of road user 2 along v1 and a clock shift enter through one combination; the identity
    # holds when the time box does not bind (state B with a defined Time Advantage)
    e = random_encounters(3000, "generic", seed=74)
    k = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, horizon=T)
    sp1 = np.linalg.norm(e.vel1, axis=1)
    along = e.vel1 / np.where(sp1 > 0, sp1, 1.0)[:, None]
    d = _dset(e, along)
    lat, tadv = d.lateral_margin(), k.tadv
    use = (k.state == "B") & np.isfinite(lat) & np.isfinite(tadv) & (tadv > 0)
    assert use.sum() > 200
    rel = np.abs(lat[use] - sp1[use] * tadv[use]) / (sp1[use] * tadv[use])
    # the box t+delta in [0,T] does not involve eps, so a few cases may differ; most agree
    assert (rel < 1e-6).mean() > 0.9
