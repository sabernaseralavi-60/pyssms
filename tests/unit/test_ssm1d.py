"""The ten car-following measures against independent time-stepping simulations of their stories."""

import numpy as np
import pytest

from pyssms.ssm1d import dcia, drac, mdrac, mpsd, psd, sdi, ttc_poly, ttcd

RNG = np.random.default_rng(7)
T = np.arange(0.0, 60.0, 1e-3)


def _first_cross(gap_t):
    """First time (s) in ``T`` where each row of ``gap_t`` is <= 0; NaN if never."""
    hit = gap_t <= 0
    idx = hit.argmax(axis=1)
    return np.where(hit.any(axis=1), T[idx], np.nan)


def _agree(a, b, tol=2e-3):
    a = np.where(a < T[-1] - 0.1, a, np.nan)  # the scan stops at 60 s: later roots count as none
    return np.isclose(a, b, atol=tol) | (np.isnan(a) & np.isnan(b))


def _closing_cases(n):
    g = RNG.uniform(5, 60, n)
    v_l = RNG.uniform(0, 20, n)
    v_f = v_l + RNG.uniform(2, 12, n)  # 2 g / dv <= 60 s: the scan window is long enough
    return g, v_l, v_f


@pytest.mark.parametrize("order", [1, 2, 3])
def test_ttc_polynomials_match_a_time_scan(order):
    n = 150
    g, v_l, v_f = _closing_cases(n)
    a_l = RNG.uniform(-2, 2, n) if order >= 2 else np.zeros(n)
    a_f = RNG.uniform(-2, 2, n) if order >= 2 else np.zeros(n)
    j_l = RNG.uniform(-0.5, 0.5, n) if order == 3 else np.zeros(n)
    j_f = RNG.uniform(-0.5, 0.5, n) if order == 3 else np.zeros(n)
    t = T[None, :]
    gap_t = (
        g[:, None]
        + (v_l - v_f)[:, None] * t
        + (a_l - a_f)[:, None] * t**2 / 2
        + (j_l - j_f)[:, None] * t**3 / 6
    )
    got = ttc_poly(g, v_l, v_f, a_l, a_f, j_l, j_f)
    assert _agree(got, _first_cross(gap_t)).all()
    assert np.isfinite(got).sum() > 50


def test_ttcd_matches_a_simulation_with_the_leader_stopping():
    n = 200
    g = RNG.uniform(5, 60, n)
    v_l = RNG.uniform(0, 20, n)
    v_f = RNG.uniform(0, 25, n)
    dec = RNG.uniform(1, 9, n)
    t = T[None, :]
    stop = (v_l / dec)[:, None]
    lead = np.where(
        t <= stop, v_l[:, None] * t - dec[:, None] * t**2 / 2, (v_l**2 / (2 * dec))[:, None]
    )
    gap_t = g[:, None] + lead - v_f[:, None] * t
    got = ttcd(g, v_l, v_f, dec)
    assert _agree(got, _first_cross(gap_t)).all()
    assert np.isfinite(got).sum() > 50


def _min_gap_with_braking(g, v_l, v_f, dec, reaction):
    """Minimum gap over time: leader at constant speed, follower brakes after ``reaction``."""
    t = T[None, :]
    follower = np.where(
        t <= reaction[:, None],
        v_f[:, None] * t,
        v_f[:, None] * reaction[:, None]
        + (
            v_f[:, None] * (t - reaction[:, None]) - dec[:, None] * (t - reaction[:, None]) ** 2 / 2
        ),
    )
    # the follower stops braking at zero speed
    t_stop = reaction + v_f / dec
    follower = np.where(
        t > t_stop[:, None], (v_f * reaction + v_f**2 / (2 * dec))[:, None], follower
    )
    return (g[:, None] + v_l[:, None] * t - follower).min(axis=1)


def test_drac_is_the_braking_that_just_avoids_the_crash():
    g, v_l, v_f = _closing_cases(200)
    d = drac(g, v_l, v_f)
    zero = np.zeros_like(g)
    assert np.abs(_min_gap_with_braking(g, v_l, v_f, d, zero)).max() < 0.05
    assert (_min_gap_with_braking(g, v_l, v_f, d * 0.97, zero) < -1e-3).all()
    assert (_min_gap_with_braking(g, v_l, v_f, d * 1.03, zero) > 1e-3).all()


def test_mdrac_is_the_braking_that_just_avoids_the_crash_after_the_reaction_time():
    g, v_l, v_f = _closing_cases(400)
    r = np.full(g.shape, 0.8)
    d = mdrac(g, v_l, v_f, r)
    ok = np.isfinite(d)
    assert ok.sum() > 100
    assert np.abs(_min_gap_with_braking(g[ok], v_l[ok], v_f[ok], d[ok], r[ok])).max() < 0.05
    # identity used in the paper: dv / (2 (TTC1 - r))
    ttc1 = ttc_poly(g, v_l, v_f)
    np.testing.assert_allclose(d[ok], ((v_f - v_l) / (2 * (ttc1 - r)))[ok], rtol=1e-9)
    # reaction time longer than TTC: no braking can help
    assert np.isinf(mdrac([10.0], [0.0], [10.0], [1.5])[0])


def test_psd_mpsd_definitions():
    assert psd([20.0], [10.0], [5.0])[0] == pytest.approx(20.0 / (100.0 / 10.0))
    assert mpsd([20.0], [10.0], [5.0], [1.0])[0] == pytest.approx(20.0 / (10.0 + 10.0))
    # the paper's Eq. (8) is the same number when its TTC is gap / v_f
    gap, v_f, dec, r = 20.0, 10.0, 5.0, 1.0
    assert mpsd([gap], [v_f], [dec], [r])[0] == pytest.approx((gap / v_f) / (r + v_f / (2 * dec)))


def test_sdi_matches_a_stopping_simulation():
    n = 500
    g = RNG.uniform(2, 60, n)
    v_l, v_f = RNG.uniform(0, 20, n), RNG.uniform(0, 25, n)
    dl, df = RNG.uniform(3, 9, n), RNG.uniform(3, 9, n)
    r = RNG.uniform(0.3, 1.5, n)
    final_gap = g + v_l**2 / (2 * dl) - (v_f * r + v_f**2 / (2 * df))
    expected = (final_gap < 0).astype(float)
    np.testing.assert_array_equal(sdi(g, v_l, v_f, dl, df, r), expected)
    assert 0.1 < expected.mean() < 0.9


def _dcia_simulate(g, v_l, v_f, a_l, a_f, r, dec):
    """Follower: acceleration a_f for r, then deceleration dec. Leader: constant a_l."""
    t = T[None, :]
    r_, af_, dec_ = r[:, None], a_f[:, None], dec[:, None]
    v_r = (v_f + a_f * r)[:, None]
    x_r = (v_f * r + a_f * r**2 / 2)[:, None]
    s = np.maximum(t - r_, 0.0)
    follower = np.where(t <= r_, v_f[:, None] * t + af_ * t**2 / 2, x_r + v_r * s - dec_ * s**2 / 2)
    speed_f = np.where(t <= r_, v_f[:, None] + af_ * t, v_r - dec_ * s)
    leader = v_l[:, None] * t + a_l[:, None] * t**2 / 2
    return g[:, None] + leader - follower, speed_f - (v_l[:, None] + a_l[:, None] * t)


def test_dcia_touches_with_equal_speeds_at_the_derived_time():
    n = 400
    g = RNG.uniform(10, 80, n)
    v_l = RNG.uniform(5, 15, n)
    v_f = v_l + RNG.uniform(2, 10, n)
    a_l, a_f = RNG.uniform(-1, 1, n), RNG.uniform(-1, 1, n)
    r = np.full(n, 1.0)
    dec, big_t = dcia(g, v_l, v_f, a_l, a_f, r)
    ok = np.isfinite(dec)
    assert ok.sum() > 100
    gap_t, rel_speed = _dcia_simulate(g[ok], v_l[ok], v_f[ok], a_l[ok], a_f[ok], r[ok], dec[ok])
    k = np.abs(T[None, :] - big_t[ok][:, None]).argmin(axis=1)
    rows = np.arange(ok.sum())
    assert np.abs(gap_t[rows, k]).max() < 5e-3
    assert np.abs(rel_speed[rows, k]).max() < 2e-2  # speed slope x half a 1 ms step
    assert (gap_t.min(axis=1) > -5e-3).all()  # never crosses before the touch


def test_printed_dcia_contact_time_differs_when_accelerations_differ():
    # printed (Fazekas et al. via Naseralavi et al. 2025, Eq. 9): T = (v_f R - v_l R - 2 D) /
    # (v_l - a_l R - v_f + a_f R). The derivation gives
    # (2 D - (v_f - v_l) R) / ((v_f - v_l) + (a_f - a_l) R).
    g, v_l, v_f, r = 40.0, 10.0, 20.0, 1.0

    def printed(a_l, a_f):
        return (v_f * r - v_l * r - 2 * g) / (v_l - a_l * r - v_f + a_f * r)

    for a_l, a_f in ((0.0, 0.0), (0.5, 0.5)):
        assert printed(a_l, a_f) == pytest.approx(dcia(g, v_l, v_f, a_l, a_f, r)[1][0])
    assert printed(0.0, 1.0) != pytest.approx(dcia(g, v_l, v_f, 0.0, 1.0, r)[1][0])
