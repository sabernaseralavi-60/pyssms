"""Stories on the overlap polygon: constant speed equals the time-time TTC; braking vs brute."""

import numpy as np
import pytest

from pyssms.reference import random_encounters
from pyssms.stories import Story, first_contact, profile
from pyssms.timetime import indicators


def _dirs(e):
    return (
        np.stack([np.cos(e.heading1), np.sin(e.heading1)], -1),
        np.stack([np.cos(e.heading2), np.sin(e.heading2)], -1),
    )


def _sat_overlap(c1, c2):
    for poly in (c1, c2):
        edge = np.roll(poly, -1, axis=0) - poly
        for nk in np.stack([edge[:, 1], -edge[:, 0]], -1):
            if (c1 @ nk).max() < (c2 @ nk).min() or (c2 @ nk).max() < (c1 @ nk).min():
                return False
    return True


def test_constant_speed_story_equals_time_time_ttc():
    e = random_encounters(3000, "generic", seed=21)
    d1, d2 = _dirs(e)
    sp1, sp2 = np.linalg.norm(e.vel1, axis=1), np.linalg.norm(e.vel2, axis=1)
    t = first_contact(
        e.shape1,
        e.pos1,
        d1,
        Story.constant_speed(sp1),
        e.shape2,
        e.pos2,
        d2,
        Story.constant_speed(sp2),
        horizon=10.0,
    )
    k = indicators(e.shape1, e.pos1, e.vel1, e.shape2, e.pos2, e.vel2, horizon=10.0)
    same = np.isclose(t, k.ttc, atol=1e-6) | (np.isnan(t) & np.isnan(k.ttc))
    # contact windows shorter than min_step (2 ms) can be missed, but never mis-timed
    wrong = ~same & np.isfinite(t)
    assert not wrong.any()
    assert (~same).sum() <= 3
    assert np.isfinite(t).sum() > 500


def test_braking_story_matches_brute_force():
    e = random_encounters(400, "generic", seed=22)
    d1, d2 = _dirs(e)
    sp1, sp2 = np.linalg.norm(e.vel1, axis=1), np.linalg.norm(e.vel2, axis=1)
    s1 = Story.constant_acceleration(sp1, -4.0)
    s2 = Story.constant_acceleration(sp2, 1.0)
    t = first_contact(e.shape1, e.pos1, d1, s1, e.shape2, e.pos2, d2, s2, horizon=10.0)
    ts1, ts2 = s1.stop_time(10.0), s2.stop_time(10.0)
    grid = np.arange(0.0, 10.0, 0.002)
    checked = 0
    for i in np.where(np.isfinite(t))[0][:60]:
        c1, c2 = e.corners1[i], e.corners2[i]
        found = np.nan
        for tt in grid:
            sg1 = s1.v0[i] * min(tt, ts1[i]) + 0.5 * s1.a[i] * min(tt, ts1[i]) ** 2
            sg2 = s2.v0[i] * min(tt, ts2[i]) + 0.5 * s2.a[i] * min(tt, ts2[i]) ** 2
            if _sat_overlap(c1 + d1[i] * sg1, c2 + d2[i] * sg2):
                found = tt
                break
        assert found == pytest.approx(t[i], abs=0.003)
        checked += 1
    assert checked >= 20


def test_profile_braking_stops_and_stays():
    s = Story.constant_acceleration([10.0], [-4.0])
    p = profile(s, horizon=10.0, dt=0.1)
    assert p["x"][0, -1] == pytest.approx(10.0**2 / (2 * 4.0))
    assert p["v"][0, -1] == 0.0 and p["a"][0, -1] == 0.0
    assert p["v"][0, 10] == pytest.approx(6.0)  # t = 1.0 s


def test_profile_constant_jerk():
    s = Story.constant_jerk([5.0], [0.0], [1.0])
    p = profile(s, horizon=4.0, dt=0.5)
    assert p["a"][0, 4] == pytest.approx(2.0)  # t = 2
    assert p["v"][0, 4] == pytest.approx(5.0 + 0.5 * 4.0)
    assert p["x"][0, 4] == pytest.approx(5.0 * 2 + 8.0 / 6.0)
